'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { getAdminRole, getAdminStats, getAdminUsers, adminChangePlan } from '@/lib/api';

const PLAN_BADGES: Record<string, { label: string; classes: string }> = {
  free: { label: 'مجاني', classes: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
  basic: { label: 'أساسي', classes: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  pro: { label: 'احترافي', classes: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300' },
  enterprise: { label: 'مؤسسي', classes: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300' },
};

const ROLE_BADGES: Record<string, { label: string; classes: string }> = {
  user: { label: 'مستخدم', classes: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
  admin: { label: 'مشرف', classes: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' },
  super_admin: { label: 'مشرف أعلى', classes: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
};

const PLAN_OPTIONS = ['free', 'basic', 'pro', 'enterprise'];

interface AdminUser {
  id: string;
  email: string;
  role: string;
  plan_tier: string;
  questions_this_month: number;
  last_active: string;
}

interface AdminStats {
  total_users: number;
  paid_users: number;
  questions_today: number;
  questions_this_month: number;
  total_conversations: number;
  total_feedback: number;
}

export default function AdminPage() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [page, setPage] = useState(0);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [changingPlan, setChangingPlan] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const PAGE_SIZE = 20;

  // Check admin role on mount
  useEffect(() => {
    getAdminRole()
      .then((data) => {
        if (data.role === 'admin' || data.role === 'super_admin') {
          setAuthorized(true);
        } else {
          setAuthorized(false);
        }
      })
      .catch(() => {
        setAuthorized(false);
      });
  }, []);

  // Load stats when authorized
  useEffect(() => {
    if (!authorized) return;
    getAdminStats()
      .then(setStats)
      .catch(console.error);
  }, [authorized]);

  // Load users
  const loadUsers = useCallback(async (pageNum: number) => {
    setLoadingUsers(true);
    try {
      const data = await getAdminUsers(PAGE_SIZE, pageNum * PAGE_SIZE);
      const userList = Array.isArray(data) ? data : (data as any).users || [];
      setUsers(userList);
      setHasMore(userList.length >= PAGE_SIZE);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingUsers(false);
    }
  }, []);

  useEffect(() => {
    if (!authorized) return;
    loadUsers(page);
  }, [authorized, page, loadUsers]);

  // Change user plan
  const handleChangePlan = async (userId: string, newPlan: string) => {
    setChangingPlan(userId);
    setMessage(null);
    try {
      await adminChangePlan(userId, newPlan);
      setMessage({ type: 'success', text: 'تم تغيير الباقة بنجاح' });
      // Refresh users
      await loadUsers(page);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'حدث خطأ' });
    } finally {
      setChangingPlan(null);
    }
  };

  // Not authorized
  if (authorized === false) {
    return (
      <div className="flex items-center justify-center min-h-screen" dir="rtl">
        <div className="glass-card p-8 text-center max-w-md">
          <div className="w-16 h-16 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">ليس لديك صلاحيات</h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">هذه الصفحة متاحة للمشرفين فقط.</p>
          <button
            onClick={() => router.push('/chat')}
            className="px-6 py-2.5 rounded-xl bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors"
          >
            العودة للمحادثة
          </button>
        </div>
      </div>
    );
  }

  // Loading state
  if (authorized === null) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 dark:border-gray-600 border-t-primary-500"></div>
      </div>
    );
  }

  const statCards = [
    { label: 'إجمالي المستخدمين', value: stats?.total_users ?? '...', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z', color: 'from-blue-500 to-blue-600' },
    { label: 'المشتركون المدفوعون', value: stats?.paid_users ?? '...', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z', color: 'from-green-500 to-green-600' },
    { label: 'أسئلة اليوم', value: stats?.questions_today ?? '...', icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z', color: 'from-amber-500 to-amber-600' },
    { label: 'أسئلة هذا الشهر', value: stats?.questions_this_month ?? '...', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', color: 'from-purple-500 to-purple-600' },
    { label: 'إجمالي المحادثات', value: stats?.total_conversations ?? '...', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10', color: 'from-teal-500 to-teal-600' },
    { label: 'إجمالي التقييمات', value: stats?.total_feedback ?? '...', icon: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z', color: 'from-pink-500 to-pink-600' },
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto" dir="rtl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold gradient-text font-heading">لوحة الإدارة</h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">إدارة المستخدمين والإحصائيات</p>
          </div>
        </div>
      </div>

      {/* Message banner */}
      {message && (
        <div className={`mb-6 p-4 rounded-xl text-sm ${
          message.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800'
            : 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800'
        }`}>
          {message.text}
        </div>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4 mb-8">
        {statCards.map((card) => (
          <div key={card.label} className="glass-card p-4">
            <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${card.color} flex items-center justify-center mb-3 shadow-sm`}>
              <svg className="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={card.icon} />
              </svg>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{card.value}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      {/* Users table */}
      <div className="glass-card overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-gray-200/50 dark:border-white/10">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white font-heading">المستخدمون</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">إدارة حسابات المستخدمين وباقاتهم</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200/50 dark:border-white/10">
                <th className="text-right px-4 sm:px-5 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">البريد</th>
                <th className="text-right px-4 sm:px-5 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">الدور</th>
                <th className="text-right px-4 sm:px-5 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">الباقة</th>
                <th className="text-right px-4 sm:px-5 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">أسئلة الشهر</th>
                <th className="text-right px-4 sm:px-5 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">آخر نشاط</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-white/5">
              {loadingUsers ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={5} className="px-4 sm:px-5 py-4">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 sm:px-5 py-8 text-center text-gray-500 dark:text-gray-400">
                    لا يوجد مستخدمون
                  </td>
                </tr>
              ) : (
                users.map((user) => {
                  const plan = PLAN_BADGES[user.plan_tier] || PLAN_BADGES.free;
                  const role = ROLE_BADGES[user.role] || ROLE_BADGES.user;

                  return (
                    <tr key={user.id} className="hover:bg-gray-50/50 dark:hover:bg-white/5 transition-colors">
                      <td className="px-4 sm:px-5 py-3">
                        <span className="text-gray-900 dark:text-gray-100 text-sm">{user.email}</span>
                      </td>
                      <td className="px-4 sm:px-5 py-3">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${role.classes}`}>
                          {role.label}
                        </span>
                      </td>
                      <td className="px-4 sm:px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${plan.classes}`}>
                            {plan.label}
                          </span>
                          <select
                            value={user.plan_tier}
                            onChange={(e) => handleChangePlan(user.id, e.target.value)}
                            disabled={changingPlan === user.id}
                            className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-surface-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:opacity-50 cursor-pointer"
                          >
                            {PLAN_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>
                                {PLAN_BADGES[opt]?.label || opt}
                              </option>
                            ))}
                          </select>
                          {changingPlan === user.id && (
                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 dark:border-gray-600 border-t-primary-500"></div>
                          )}
                        </div>
                      </td>
                      <td className="px-4 sm:px-5 py-3">
                        <span className="text-gray-700 dark:text-gray-300">{user.questions_this_month ?? 0}</span>
                      </td>
                      <td className="px-4 sm:px-5 py-3">
                        <span className="text-gray-500 dark:text-gray-400 text-xs">
                          {user.last_active
                            ? new Date(user.last_active).toLocaleDateString('ar-SA', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '---'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-t border-gray-200/50 dark:border-white/10">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            صفحة {page + 1}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              السابق
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
              className="px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              التالي
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
