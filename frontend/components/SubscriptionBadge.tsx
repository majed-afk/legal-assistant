'use client';

import { useSubscription } from '@/lib/supabase/subscription-context';

const tierConfig: Record<string, { label: string; className: string }> = {
  free: {
    label: 'مجاني',
    className: 'bg-gray-500/20 text-gray-300',
  },
  basic: {
    label: 'أساسي',
    className: 'bg-primary-500/20 text-primary-300',
  },
  pro: {
    label: 'احترافي',
    className: 'bg-gold-500/20 text-gold-400',
  },
  enterprise: {
    label: 'مؤسسي',
    className: 'bg-purple-500/20 text-purple-300',
  },
};

export default function SubscriptionBadge() {
  const { subscription, loading } = useSubscription();

  if (loading) return null;

  const tier = subscription?.plan_tier || 'free';
  const config = tierConfig[tier] || tierConfig.free;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
