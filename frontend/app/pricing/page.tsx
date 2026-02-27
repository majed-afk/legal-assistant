'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import PricingCard from '@/components/PricingCard';
import { getPlans } from '@/lib/api';

export default function PricingPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    getPlans()
      .then((data) => setPlans(data.plans || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSubscribe = (tier: string) => {
    if (tier === 'free') {
      router.push('/login');
    } else {
      // Redirect to login first, then they can subscribe from /subscription
      router.push(`/login?redirect=/subscription&plan=${tier}&cycle=${billingCycle}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-50 to-primary-50/30" dir="rtl">
      {/* Header */}
      <header className="py-6 px-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
              </svg>
            </div>
            <span className="text-primary-700 font-bold text-lg font-heading">Sanad AI</span>
          </Link>
          <Link
            href="/login"
            className="px-4 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors"
          >
            تسجيل الدخول
          </Link>
        </div>
      </header>

      {/* Hero */}
      <div className="text-center pt-8 pb-12 px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 font-heading mb-4">
          اختر الباقة المناسبة لك
        </h1>
        <p className="text-gray-600 text-lg max-w-2xl mx-auto mb-8">
          مستشارك القانوني الذكي — متخصص في الأنظمة السعودية
        </p>

        {/* Billing toggle */}
        <div className="inline-flex items-center gap-3 bg-white rounded-xl p-1.5 shadow-sm border border-gray-200">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
              billingCycle === 'monthly'
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            شهري
          </button>
          <button
            onClick={() => setBillingCycle('yearly')}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
              billingCycle === 'yearly'
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            سنوي
            <span className="mr-1 text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">وفّر 20%</span>
          </button>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="max-w-7xl mx-auto px-4 pb-20">
        {loading ? (
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
                onSubscribe={handleSubscribe}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8 px-4 text-center">
        <p className="text-gray-500 text-sm">
          جميع الأسعار بالريال السعودي — تشمل ضريبة القيمة المضافة
        </p>
        <div className="flex items-center justify-center gap-4 mt-3">
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
            دفع آمن عبر Moyasar
          </span>
          <Link href="/privacy" className="text-xs text-gray-400 hover:text-gray-600">سياسة الخصوصية</Link>
        </div>
      </footer>
    </div>
  );
}
