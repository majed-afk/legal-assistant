-- ============================================================
-- Sanad AI — Subscription System Schema
-- Phase 2: Plans, Subscriptions, Payments, Usage Tracking
-- ============================================================

-- 1. Subscription Plans (static — seeded once)
CREATE TABLE IF NOT EXISTS subscription_plans (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tier TEXT UNIQUE NOT NULL CHECK (tier IN ('free','basic','pro','enterprise')),
  name_ar TEXT NOT NULL,
  name_en TEXT NOT NULL,
  price_monthly_sar INTEGER NOT NULL DEFAULT 0,
  price_yearly_sar INTEGER NOT NULL DEFAULT 0,
  limits JSONB NOT NULL DEFAULT '{}',
  features JSONB NOT NULL DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Seed plan data
INSERT INTO subscription_plans (tier, name_ar, name_en, price_monthly_sar, price_yearly_sar, limits, features) VALUES
('free', 'مجاني', 'Free', 0, 0,
  '{"questions_per_day":3,"questions_per_month":30,"drafts_per_month":1,"deadlines_per_month":3,"conversations":5}',
  '{"model_modes":["1.1"],"pdf_export":false}'),
('basic', 'أساسي', 'Basic', 49, 470,
  '{"questions_per_day":20,"questions_per_month":400,"drafts_per_month":10,"deadlines_per_month":20,"conversations":50}',
  '{"model_modes":["1.1","2.1"],"pdf_export":true}'),
('pro', 'احترافي', 'Pro', 149, 1430,
  '{"questions_per_day":-1,"questions_per_month":-1,"drafts_per_month":-1,"deadlines_per_month":-1,"conversations":-1}',
  '{"model_modes":["1.1","2.1"],"pdf_export":true,"document_review":true}'),
('enterprise', 'مؤسسي', 'Enterprise', 499, 4790,
  '{"questions_per_day":-1,"questions_per_month":-1,"drafts_per_month":-1,"deadlines_per_month":-1,"conversations":-1}',
  '{"model_modes":["1.1","2.1"],"pdf_export":true,"document_review":true,"api_access":true}')
ON CONFLICT (tier) DO NOTHING;


-- 2. User Subscriptions
CREATE TABLE IF NOT EXISTS user_subscriptions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES subscription_plans(id),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','canceled','past_due','expired')),
  billing_cycle TEXT DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly','yearly')),
  moyasar_payment_id TEXT,
  current_period_start TIMESTAMPTZ NOT NULL DEFAULT now(),
  current_period_end TIMESTAMPTZ NOT NULL,
  cancel_at_period_end BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Only one active subscription per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_active_sub
  ON user_subscriptions(user_id) WHERE status = 'active';


-- 3. Payment Transactions
CREATE TABLE IF NOT EXISTS payment_transactions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  subscription_id UUID REFERENCES user_subscriptions(id),
  amount_sar INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('initiated','paid','failed','refunded')),
  moyasar_payment_id TEXT,
  payment_method TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payment_user ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_moyasar ON payment_transactions(moyasar_payment_id);


-- 4. Usage Tracking (one row per user per day)
CREATE TABLE IF NOT EXISTS usage_tracking (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  questions_count INTEGER DEFAULT 0,
  drafts_count INTEGER DEFAULT 0,
  deadlines_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_usage_user_date ON usage_tracking(user_id, date);


-- ============================================================
-- Helper Functions
-- ============================================================

-- Atomic increment for usage counters
CREATE OR REPLACE FUNCTION increment_usage(
  p_user_id UUID,
  p_field TEXT
) RETURNS INTEGER AS $$
DECLARE
  v_count INTEGER;
BEGIN
  -- Ensure row exists for today
  INSERT INTO usage_tracking (user_id, date, questions_count, drafts_count, deadlines_count)
  VALUES (p_user_id, CURRENT_DATE, 0, 0, 0)
  ON CONFLICT (user_id, date) DO NOTHING;

  -- Atomically increment the specified field
  EXECUTE format(
    'UPDATE usage_tracking SET %I = %I + 1 WHERE user_id = $1 AND date = CURRENT_DATE RETURNING %I',
    p_field, p_field, p_field
  ) INTO v_count USING p_user_id;

  RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Get monthly usage totals for a user
CREATE OR REPLACE FUNCTION get_monthly_usage(p_user_id UUID)
RETURNS TABLE(questions INTEGER, drafts INTEGER, deadlines INTEGER) AS $$
BEGIN
  RETURN QUERY
  SELECT
    COALESCE(SUM(questions_count), 0)::INTEGER,
    COALESCE(SUM(drafts_count), 0)::INTEGER,
    COALESCE(SUM(deadlines_count), 0)::INTEGER
  FROM usage_tracking
  WHERE user_id = p_user_id
    AND date >= date_trunc('month', CURRENT_DATE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Get user's active subscription with plan details
CREATE OR REPLACE FUNCTION get_user_subscription(p_user_id UUID)
RETURNS TABLE(
  subscription_id UUID,
  plan_tier TEXT,
  plan_name_ar TEXT,
  plan_name_en TEXT,
  plan_limits JSONB,
  plan_features JSONB,
  sub_status TEXT,
  billing_cycle TEXT,
  current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    us.id,
    sp.tier,
    sp.name_ar,
    sp.name_en,
    sp.limits,
    sp.features,
    us.status,
    us.billing_cycle,
    us.current_period_end,
    us.cancel_at_period_end
  FROM user_subscriptions us
  JOIN subscription_plans sp ON sp.id = us.plan_id
  WHERE us.user_id = p_user_id
    AND us.status = 'active'
  LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================
-- Row Level Security (RLS)
-- ============================================================

-- Plans: public read
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "plans_public_read" ON subscription_plans;
CREATE POLICY "plans_public_read" ON subscription_plans
  FOR SELECT USING (true);

-- Subscriptions: users read own
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_read_own_sub" ON user_subscriptions;
CREATE POLICY "users_read_own_sub" ON user_subscriptions
  FOR SELECT USING (auth.uid() = user_id);

-- Payments: users read own
ALTER TABLE payment_transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_read_own_payments" ON payment_transactions;
CREATE POLICY "users_read_own_payments" ON payment_transactions
  FOR SELECT USING (auth.uid() = user_id);

-- Usage: users read own
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_read_own_usage" ON usage_tracking;
CREATE POLICY "users_read_own_usage" ON usage_tracking
  FOR SELECT USING (auth.uid() = user_id);


-- ============================================================
-- Migration: Assign free plan to existing users
-- ============================================================
-- Run this AFTER the tables and seed data are created:
--
-- INSERT INTO user_subscriptions (user_id, plan_id, current_period_end)
-- SELECT u.id, p.id, '2099-12-31'::TIMESTAMPTZ
-- FROM auth.users u
-- CROSS JOIN subscription_plans p
-- WHERE p.tier = 'free'
--   AND NOT EXISTS (SELECT 1 FROM user_subscriptions s WHERE s.user_id = u.id AND s.status = 'active');
