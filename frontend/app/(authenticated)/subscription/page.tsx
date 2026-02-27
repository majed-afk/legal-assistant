'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useSubscription } from '@/lib/supabase/subscription-context';
import { createSubscription, cancelSubscription } from '@/lib/api';
import PricingCard from '@/components/PricingCard';
import { getPlans } from '@/lib/api';

export default function SubscriptionPage() {
  const { subscription, usage, loading, refreshSubscription, refreshUsage } = useSubscription();
  const [plans, setPlans] = useState<any[]>([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const router = useRouter();

  useEffect(() => {
    getPlans()
      .then((data) => setPlans(data.plans || []))
      .catch(console.error)
      .finally(() => setPlansLoading(false));
  }, []);

  const handleSubscribe = async (tier: string) => {
    if (tier === 'free') return;

    setActionLoading(tier);
    setMessage(null);

    try {
      const result = await createSubscription(tier, billingCycle);
      // For Moyasar, we'd redirect to payment page
      // For now, show the payment data
      if (result.callback_url) {
        // In production: integrate Moyasar.js for client-side payment form
        setMessage({
          type: 'success',
          text: `تم إنشاء طلب الدفع — المبلغ: ${result.plan.price_sar} ر.س`,
        });
      }
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancel = async () => {
    setActionLoading('cancel');
    setMessage(null);

    try {
      const result = await cancelSubscription();
      setMessage({ type: 'success', text: result.message });
      setCancelConfirm(false);
      await refreshSubscription();
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8" dir="rtl">
      <h1 className="text-2xl font-bold text-gray-900 mb-2 font-heading">إدارة الاشتراك</h1>
      <p className="text-gray-500 text-sm mb-8">تحكم في باقتك واستخدامك</p>

      {/* Message banner */}
      {message && (
        <div className={`mb-6 p-4 rounded-xl text-sm ${
          message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      {/* Current subscription summary */}
      {!loading && subscription && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-8 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                باقة {subscription.plan_name_ar}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {subscription.plan_tier === 'free'
                  ? 'باقة مجانية — ترقَّ للحصول على ميزات إضافية'
                  : subscription.cancel_at_period_end
                  ? `سينتهي الاشتراك في ${new Date(subscription.current_period_end || '').toLocaleDateString('ar-SA')}`
                  : `يتجدد تلقائياً في ${new Date(subscription.current_period_end || '').toLocaleDateString('ar-SA')}`
                }
              </p>
            </div>
            {subscription.plan_tier !== 'free' && !subscription.cancel_at_period_end && (
              <button
                onClick={() => setCancelConfirm(true)}
                className="px-4 py-2 rounded-lg border border-red-200 text-red-600 text-sm hover:bg-red-50 transition-colors"
              >
                إلغاء الاشتراك
              </button>
            )}
          </div>

          {/* Usage bars */}
          {usage && (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <UsageBarInline
                label="الأسئلة اليوم"
                current={usage.today.questions_count}
                limit={usage.limits.questions_per_day}
              />
              <UsageBarInline
                label="الأسئلة هذا الشهر"
                current={usage.monthly.questions}
                limit={usage.limits.questions_per_month}
              />
              <UsageBarInline
                label="المذكرات هذا الشهر"
                current={usage.monthly.drafts}
                limit={usage.limits.drafts_per_month}
              />
            </div>
          )}
        </div>
      )}

      {/* Cancel confirmation modal */}
      {cancelConfirm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setCancelConfirm(false)}>
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-gray-900 mb-2">تأكيد إلغاء الاشتراك</h3>
            <p className="text-gray-600 text-sm mb-6">
              سيتم إلغاء اشتراكك في نهاية الفترة الحالية. ستبقى جميع الميزات متاحة حتى ذلك الحين.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleCancel}
                disabled={actionLoading === 'cancel'}
                className="flex-1 py-2.5 rounded-xl bg-red-500 text-white font-medium text-sm hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                {actionLoading === 'cancel' ? 'جاري الإلغاء...' : 'تأكيد الإلغاء'}
              </button>
              <button
                onClick={() => setCancelConfirm(false)}
                className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-700 font-medium text-sm hover:bg-gray-200 transition-colors"
              >
                تراجع
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Billing toggle */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900 font-heading">الباقات المتاحة</h2>
        <div className="inline-flex items-center gap-2 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              billingCycle === 'monthly' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'
            }`}
          >
            شهري
          </button>
          <button
            onClick={() => setBillingCycle('yearly')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              billingCycle === 'yearly' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'
            }`}
          >
            سنوي
          </button>
        </div>
      </div>

      {/* Pricing cards */}
      {plansLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-96 rounded-2xl bg-white animate-pulse border border-gray-200" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan) => (
            <PricingCard
              key={plan.id || plan.tier}
              tier={plan.tier}
              nameAr={plan.name_ar}
              priceMonthly={plan.price_monthly_sar}
              priceYearly={plan.price_yearly_sar}
              limits={plan.limits}
              features={plan.features}
              billingCycle={billingCycle}
              isCurrentPlan={subscription?.plan_tier === plan.tier}
              onSubscribe={handleSubscribe}
              loading={actionLoading === plan.tier}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function UsageBarInline({
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
  const barColor = percentage >= 90 ? 'bg-red-500' : percentage >= 70 ? 'bg-yellow-500' : 'bg-green-500';

  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-600">{label}</span>
        <span className="text-sm font-medium text-gray-900">
          {isUnlimited ? `${current}` : `${current}/${limit}`}
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
      {isUnlimited && (
        <div className="text-xs text-gray-400">غير محدود</div>
      )}
    </div>
  );
}
