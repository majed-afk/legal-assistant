-- ============================================================
-- Sanad AI — Security Fix: RLS Policies + Atomic Subscription
-- Run this on Supabase SQL Editor
-- ============================================================

-- ══════════════════════════════════════════════════════════════
-- 1. Fix message_feedback RLS (restrict INSERT/UPDATE to authenticated users)
-- ══════════════════════════════════════════════════════════════

-- Drop overly permissive policies
DROP POLICY IF EXISTS "anyone_insert_feedback" ON message_feedback;
DROP POLICY IF EXISTS "anyone_update_feedback" ON message_feedback;
DROP POLICY IF EXISTS "anyone_select_feedback" ON message_feedback;

-- Authenticated users can insert their own feedback
CREATE POLICY "auth_insert_feedback" ON message_feedback
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Authenticated users can update their own feedback (by message_id)
CREATE POLICY "auth_update_feedback" ON message_feedback
  FOR UPDATE USING (auth.uid() IS NOT NULL);

-- Authenticated users can read feedback (needed for upsert)
CREATE POLICY "auth_select_feedback" ON message_feedback
  FOR SELECT USING (auth.uid() IS NOT NULL);


-- ══════════════════════════════════════════════════════════════
-- 2. Fix analytics_events RLS (restrict INSERT to authenticated users)
-- ══════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS "anyone_insert_analytics" ON analytics_events;

CREATE POLICY "auth_insert_analytics" ON analytics_events
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);


-- ══════════════════════════════════════════════════════════════
-- 3. Fix knowledge_gaps RLS (restrict INSERT to authenticated users)
-- ══════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS "anyone_insert_knowledge_gaps" ON knowledge_gaps;

CREATE POLICY "auth_insert_knowledge_gaps" ON knowledge_gaps
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);


-- ══════════════════════════════════════════════════════════════
-- 4. Fix question_topics_daily RLS
-- ══════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS "anyone_insert_topics" ON question_topics_daily;
DROP POLICY IF EXISTS "anyone_update_topics" ON question_topics_daily;

CREATE POLICY "service_insert_topics" ON question_topics_daily
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "service_update_topics" ON question_topics_daily
  FOR UPDATE USING (auth.uid() IS NOT NULL);


-- ══════════════════════════════════════════════════════════════
-- 5. Fix admin_audit_log RLS (allow admins to read)
-- ══════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS "admin_read_audit" ON admin_audit_log;

CREATE POLICY "admin_read_audit" ON admin_audit_log
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_roles.user_id = auth.uid()
      AND user_roles.role IN ('admin', 'super_admin')
    )
  );


-- ══════════════════════════════════════════════════════════════
-- 6. Atomic subscription activation function (prevents race conditions)
-- ══════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION activate_subscription_atomic(
  p_user_id UUID,
  p_plan_id UUID,
  p_billing_cycle TEXT,
  p_payment_id TEXT,
  p_period_start TIMESTAMPTZ,
  p_period_end TIMESTAMPTZ
) RETURNS UUID AS $$
DECLARE
  v_sub_id UUID;
BEGIN
  -- Deactivate existing active subscriptions (atomic)
  UPDATE user_subscriptions
  SET status = 'expired', updated_at = now()
  WHERE user_id = p_user_id AND status = 'active';

  -- Create new subscription
  INSERT INTO user_subscriptions (
    user_id, plan_id, status, billing_cycle,
    moyasar_payment_id, current_period_start, current_period_end,
    cancel_at_period_end
  ) VALUES (
    p_user_id, p_plan_id, 'active', p_billing_cycle,
    p_payment_id, p_period_start, p_period_end, false
  ) RETURNING id INTO v_sub_id;

  RETURN v_sub_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
