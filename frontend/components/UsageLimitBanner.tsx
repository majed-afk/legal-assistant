'use client';

import Link from 'next/link';
import { useSubscription } from '@/lib/supabase/subscription-context';

interface UsageLimitBannerProps {
  /** The action type to check */
  action?: 'questions' | 'drafts' | 'deadlines';
}

export default function UsageLimitBanner({ action = 'questions' }: UsageLimitBannerProps) {
  const { canPerformAction, getRemainingCount, subscription, loading } = useSubscription();

  if (loading) return null;

  const remaining = getRemainingCount(action);
  const canPerform = canPerformAction(action);
  const tier = subscription?.plan_tier || 'free';

  // Don't show banner for unlimited plans
  if (remaining === -1) return null;

  // Show warning when 90% reached (remaining <= 10% of limit)
  if (canPerform && remaining > 3) return null;

  if (!canPerform) {
    // Limit reached
    return (
      <div className="mx-4 mb-3 p-3 rounded-xl bg-red-50 border border-red-200 flex items-center justify-between gap-3 animate-fade-in">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <span className="text-red-700 text-sm">
            وصلت للحد المسموح في باقة {subscription?.plan_name_ar || 'المجانية'}
          </span>
        </div>
        <Link
          href="/subscription"
          className="px-3 py-1.5 rounded-lg bg-primary-500 text-white text-xs font-medium hover:bg-primary-600 transition-colors whitespace-nowrap"
        >
          ترقية الباقة
        </Link>
      </div>
    );
  }

  // Approaching limit
  return (
    <div className="mx-4 mb-3 p-3 rounded-xl bg-yellow-50 border border-yellow-200 flex items-center justify-between gap-3 animate-fade-in">
      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-yellow-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-yellow-800 text-sm">
          بقي لك {remaining} {action === 'questions' ? 'سؤال' : action === 'drafts' ? 'مذكرة' : 'حساب مهلة'} فقط
        </span>
      </div>
      {tier === 'free' && (
        <Link
          href="/subscription"
          className="px-3 py-1.5 rounded-lg bg-primary-500 text-white text-xs font-medium hover:bg-primary-600 transition-colors whitespace-nowrap"
        >
          ترقية
        </Link>
      )}
    </div>
  );
}
