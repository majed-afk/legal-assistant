-- ============================================================
-- Sanad AI — RBAC (Role-Based Access Control)
-- Admin roles and permissions system
-- ============================================================

-- 1. User Roles table
CREATE TABLE IF NOT EXISTS user_roles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'super_admin')),
  granted_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role);

-- RLS: users can read own role, admins can read all
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_read_own_role" ON user_roles;
CREATE POLICY "users_read_own_role" ON user_roles
  FOR SELECT USING (auth.uid() = user_id);

-- 2. Admin audit log
CREATE TABLE IF NOT EXISTS admin_audit_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  admin_user_id UUID NOT NULL REFERENCES auth.users(id),
  action TEXT NOT NULL,
  target_user_id UUID REFERENCES auth.users(id),
  details JSONB DEFAULT '{}',
  ip_address TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_admin ON admin_audit_log(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON admin_audit_log(created_at DESC);

ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;
-- Only service role can write, admins can read (via backend with service key)

-- 3. Helper function: Check if user is admin
CREATE OR REPLACE FUNCTION is_admin(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM user_roles
    WHERE user_id = p_user_id
    AND role IN ('admin', 'super_admin')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Helper function: Get user role
CREATE OR REPLACE FUNCTION get_user_role(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
  v_role TEXT;
BEGIN
  SELECT role INTO v_role FROM user_roles WHERE user_id = p_user_id;
  RETURN COALESCE(v_role, 'user');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Admin stats function (for dashboard)
CREATE OR REPLACE FUNCTION get_admin_stats()
RETURNS TABLE(
  total_users BIGINT,
  active_subscribers BIGINT,
  free_users BIGINT,
  paid_users BIGINT,
  questions_today BIGINT,
  questions_this_month BIGINT,
  total_conversations BIGINT,
  total_feedback BIGINT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    (SELECT count(*) FROM auth.users)::BIGINT,
    (SELECT count(*) FROM user_subscriptions WHERE status = 'active')::BIGINT,
    (SELECT count(*) FROM user_subscriptions us JOIN subscription_plans sp ON sp.id = us.plan_id WHERE us.status = 'active' AND sp.tier = 'free')::BIGINT,
    (SELECT count(*) FROM user_subscriptions us JOIN subscription_plans sp ON sp.id = us.plan_id WHERE us.status = 'active' AND sp.tier != 'free')::BIGINT,
    (SELECT COALESCE(sum(questions_count), 0) FROM usage_tracking WHERE date = CURRENT_DATE)::BIGINT,
    (SELECT COALESCE(sum(questions_count), 0) FROM usage_tracking WHERE date >= date_trunc('month', CURRENT_DATE))::BIGINT,
    (SELECT count(*) FROM conversations)::BIGINT,
    (SELECT count(*) FROM message_feedback)::BIGINT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Get all users with details (for admin dashboard)
CREATE OR REPLACE FUNCTION get_admin_users(
  p_limit INTEGER DEFAULT 50,
  p_offset INTEGER DEFAULT 0
)
RETURNS TABLE(
  user_id UUID,
  email TEXT,
  created_at TIMESTAMPTZ,
  role TEXT,
  plan_tier TEXT,
  plan_name_ar TEXT,
  questions_this_month BIGINT,
  last_active DATE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    u.id,
    u.email::TEXT,
    u.created_at,
    COALESCE(ur.role, 'user')::TEXT,
    COALESCE(sp.tier, 'free')::TEXT,
    COALESCE(sp.name_ar, 'مجاني')::TEXT,
    COALESCE((
      SELECT sum(ut.questions_count)
      FROM usage_tracking ut
      WHERE ut.user_id = u.id AND ut.date >= date_trunc('month', CURRENT_DATE)
    ), 0)::BIGINT,
    (SELECT max(ut.date) FROM usage_tracking ut WHERE ut.user_id = u.id)
  FROM auth.users u
  LEFT JOIN user_roles ur ON ur.user_id = u.id
  LEFT JOIN user_subscriptions us ON us.user_id = u.id AND us.status = 'active'
  LEFT JOIN subscription_plans sp ON sp.id = us.plan_id
  ORDER BY u.created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
