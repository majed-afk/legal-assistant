'use client';

interface PricingCardProps {
  tier: string;
  nameAr: string;
  priceMonthly: number;
  priceYearly: number;
  limits: {
    questions_per_day: number;
    questions_per_month: number;
    drafts_per_month: number;
    deadlines_per_month: number;
    conversations: number;
  };
  features: {
    model_modes: string[];
    pdf_export: boolean;
    document_review?: boolean;
    api_access?: boolean;
  };
  isCurrentPlan?: boolean;
  billingCycle: 'monthly' | 'yearly';
  onSubscribe?: (tier: string) => void;
  loading?: boolean;
}

const tierColors: Record<string, { gradient: string; badge: string; border: string }> = {
  free: {
    gradient: 'from-gray-500 to-gray-600',
    badge: 'bg-gray-100 text-gray-700',
    border: 'border-gray-200',
  },
  basic: {
    gradient: 'from-primary-500 to-primary-600',
    badge: 'bg-primary-100 text-primary-700',
    border: 'border-primary-200',
  },
  pro: {
    gradient: 'from-gold-500 to-gold-600',
    badge: 'bg-gold-300/20 text-gold-700',
    border: 'border-gold-400/30',
  },
  enterprise: {
    gradient: 'from-purple-500 to-purple-700',
    badge: 'bg-purple-100 text-purple-700',
    border: 'border-purple-200',
  },
};

function formatLimit(value: number, unit: string): string {
  if (value === -1) return 'غير محدود';
  return `${value} ${unit}`;
}

export default function PricingCard({
  tier,
  nameAr,
  priceMonthly,
  priceYearly,
  limits,
  features,
  isCurrentPlan,
  billingCycle,
  onSubscribe,
  loading,
}: PricingCardProps) {
  const colors = tierColors[tier] || tierColors.free;
  const price = billingCycle === 'yearly' ? Math.round(priceYearly / 12) : priceMonthly;
  const isPopular = tier === 'pro';

  return (
    <div
      className={`relative rounded-2xl border-2 ${
        isPopular ? 'border-gold-400 shadow-glow-gold' : colors.border
      } bg-white p-6 flex flex-col transition-all duration-300 hover:shadow-elevated-lg ${
        isCurrentPlan ? 'ring-2 ring-primary-500' : ''
      }`}
    >
      {/* Popular badge */}
      {isPopular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-gradient-to-r from-gold-500 to-gold-600 text-white text-xs font-bold px-4 py-1 rounded-full shadow-sm">
            الأكثر شعبية
          </span>
        </div>
      )}

      {/* Current plan badge */}
      {isCurrentPlan && (
        <div className="absolute -top-3 right-4">
          <span className="bg-primary-500 text-white text-xs font-bold px-3 py-1 rounded-full">
            باقتك الحالية
          </span>
        </div>
      )}

      {/* Header */}
      <div className="text-center mb-6">
        <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium mb-3 ${colors.badge}`}>
          {nameAr}
        </div>
        <div className="mt-2">
          {priceMonthly === 0 ? (
            <span className="text-4xl font-bold text-gray-900">مجاني</span>
          ) : (
            <>
              <span className="text-4xl font-bold text-gray-900">{price}</span>
              <span className="text-gray-500 text-sm mr-1">ر.س/شهر</span>
              {billingCycle === 'yearly' && (
                <div className="text-xs text-green-600 mt-1">وفّر {Math.round((1 - priceYearly / (priceMonthly * 12)) * 100)}%</div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Features list */}
      <div className="flex-1 space-y-3 mb-6">
        <FeatureItem
          text={`${formatLimit(limits.questions_per_day, 'سؤال/يوم')}`}
          included
        />
        <FeatureItem
          text={`${formatLimit(limits.questions_per_month, 'سؤال/شهر')}`}
          included
        />
        <FeatureItem
          text={`${formatLimit(limits.drafts_per_month, 'مذكرة/شهر')}`}
          included
        />
        <FeatureItem
          text={`${formatLimit(limits.deadlines_per_month, 'حساب مهلة/شهر')}`}
          included
        />
        <FeatureItem
          text={`${formatLimit(limits.conversations, 'محادثة')}`}
          included
        />
        <FeatureItem
          text="وضع الإجابة المفصّل (2.1)"
          included={features.model_modes.includes('2.1')}
        />
        <FeatureItem
          text="تصدير PDF"
          included={features.pdf_export}
        />
        <FeatureItem
          text="مراجعة المستندات"
          included={features.document_review || false}
        />
        <FeatureItem
          text="API خارجي"
          included={features.api_access || false}
        />
      </div>

      {/* CTA Button */}
      <button
        onClick={() => onSubscribe?.(tier)}
        disabled={isCurrentPlan || loading}
        className={`w-full py-3 px-4 rounded-xl font-medium text-sm transition-all duration-300 ${
          isCurrentPlan
            ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
            : isPopular
            ? 'bg-gradient-to-r from-gold-500 to-gold-600 text-white hover:shadow-glow-gold'
            : tier === 'free'
            ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            : 'bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:shadow-glow'
        } ${loading ? 'opacity-50 cursor-wait' : ''}`}
      >
        {loading ? 'جاري المعالجة...' : isCurrentPlan ? 'باقتك الحالية' : tier === 'free' ? 'ابدأ مجاناً' : 'اشترك الآن'}
      </button>
    </div>
  );
}

function FeatureItem({ text, included }: { text: string; included: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {included ? (
        <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-4 h-4 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      <span className={included ? 'text-gray-700' : 'text-gray-400'}>{text}</span>
    </div>
  );
}
