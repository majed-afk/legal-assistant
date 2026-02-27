'use client';

import { useSubscription } from '@/lib/supabase/subscription-context';

interface UsageBarProps {
  /** Compact mode for sidebar display */
  compact?: boolean;
}

export default function UsageBar({ compact = false }: UsageBarProps) {
  const { usage, loading } = useSubscription();

  if (loading || !usage) return null;

  const dailyLimit = usage.limits.questions_per_day;
  const isUnlimited = dailyLimit === -1;
  const current = usage.today.questions_count;
  const percentage = isUnlimited ? 0 : Math.min(100, (current / dailyLimit) * 100);

  const barColor =
    percentage >= 90 ? 'bg-red-500' : percentage >= 70 ? 'bg-yellow-500' : 'bg-primary-400';

  if (compact) {
    if (isUnlimited) return null; // Don't show bar for unlimited plans in compact mode

    return (
      <div className="px-3 py-2">
        <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1">
          <span>الأسئلة اليوم</span>
          <span>{current}/{dailyLimit}</span>
        </div>
        <div className="h-1 bg-white/10 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <UsageRow
        label="الأسئلة اليوم"
        current={usage.today.questions_count}
        limit={usage.limits.questions_per_day}
      />
      <UsageRow
        label="الأسئلة هذا الشهر"
        current={usage.monthly.questions}
        limit={usage.limits.questions_per_month}
      />
      <UsageRow
        label="المذكرات هذا الشهر"
        current={usage.monthly.drafts}
        limit={usage.limits.drafts_per_month}
      />
      <UsageRow
        label="حاسبة المهل هذا الشهر"
        current={usage.monthly.deadlines}
        limit={usage.limits.deadlines_per_month}
      />
    </div>
  );
}

function UsageRow({
  label,
  current,
  limit,
}: {
  label: string;
  current: number;
  limit: number;
}) {
  const isUnlimited = limit === -1;
  const percentage = isUnlimited ? 0 : Math.min(100, (current / limit) * 100);
  const barColor =
    percentage >= 90 ? 'bg-red-500' : percentage >= 70 ? 'bg-yellow-500' : 'bg-green-500';

  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="text-gray-900 font-medium">
          {isUnlimited ? (
            <span className="text-green-600 text-xs">غير محدود</span>
          ) : (
            `${current}/${limit}`
          )}
        </span>
      </div>
      {!isUnlimited && (
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
    </div>
  );
}
