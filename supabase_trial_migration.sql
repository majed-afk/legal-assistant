-- ============================================================
-- Migration: Add trial usage tracking for free users
-- Run this on Supabase SQL editor
-- ============================================================

-- 1. Create trial_usage table
CREATE TABLE IF NOT EXISTS trial_usage (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  feature TEXT NOT NULL,           -- e.g., 'model_mode_2.1'
  usage_count INTEGER DEFAULT 0,
  max_allowed INTEGER DEFAULT 3,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, feature)
);

CREATE INDEX IF NOT EXISTS idx_trial_usage_user_feature
  ON trial_usage(user_id, feature);

-- 2. RLS
ALTER TABLE trial_usage ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_read_own_trial_usage" ON trial_usage;
CREATE POLICY "users_read_own_trial_usage" ON trial_usage
  FOR SELECT USING (auth.uid() = user_id);

-- 3. Get trial usage for a user+feature
CREATE OR REPLACE FUNCTION get_trial_usage(
  p_user_id UUID,
  p_feature TEXT
) RETURNS TABLE(current_count INTEGER, max_count INTEGER) AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.usage_count::INTEGER,
    t.max_allowed::INTEGER
  FROM trial_usage t
  WHERE t.user_id = p_user_id AND t.feature = p_feature;

  -- If no row exists, return 0/3
  IF NOT FOUND THEN
    RETURN QUERY SELECT 0::INTEGER, 3::INTEGER;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Atomic check-and-increment for trial usage
CREATE OR REPLACE FUNCTION increment_trial_usage(
  p_user_id UUID,
  p_feature TEXT,
  p_max_allowed INTEGER DEFAULT 3
) RETURNS TABLE(current_count INTEGER, max_count INTEGER, allowed BOOLEAN) AS $$
DECLARE
  v_count INTEGER;
BEGIN
  -- Upsert: create row if not exists
  INSERT INTO trial_usage (user_id, feature, usage_count, max_allowed)
  VALUES (p_user_id, p_feature, 0, p_max_allowed)
  ON CONFLICT (user_id, feature) DO NOTHING;

  -- Check current count BEFORE incrementing (with row lock)
  SELECT t.usage_count INTO v_count
  FROM trial_usage t
  WHERE t.user_id = p_user_id AND t.feature = p_feature
  FOR UPDATE;

  IF v_count >= p_max_allowed THEN
    -- Already at limit, do not increment
    RETURN QUERY SELECT v_count, p_max_allowed, false;
    RETURN;
  END IF;

  -- Increment
  UPDATE trial_usage
  SET usage_count = usage_count + 1, updated_at = now()
  WHERE user_id = p_user_id AND feature = p_feature
  RETURNING usage_count INTO v_count;

  RETURN QUERY SELECT v_count, p_max_allowed, true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
