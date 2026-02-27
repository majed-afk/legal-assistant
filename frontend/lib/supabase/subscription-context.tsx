'use client';

import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useAuth } from './auth-context';
import { getSubscription, getUsage } from '@/lib/api';

interface PlanInfo {
  tier: string;
  name_ar: string;
  name_en: string;
}

interface UsageLimits {
  questions_per_day: number;
  questions_per_month: number;
  drafts_per_month: number;
  deadlines_per_month: number;
  conversations: number;
}

interface PlanFeatures {
  model_modes: string[];
  pdf_export: boolean;
  document_review?: boolean;
  api_access?: boolean;
}

interface UsageToday {
  questions_count: number;
  drafts_count: number;
  deadlines_count: number;
}

interface UsageMonthly {
  questions: number;
  drafts: number;
  deadlines: number;
}

interface SubscriptionData {
  subscription_id: string | null;
  plan_tier: string;
  plan_name_ar: string;
  plan_name_en: string;
  limits: UsageLimits;
  features: PlanFeatures;
  status: string;
  billing_cycle: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

interface UsageData {
  plan: PlanInfo;
  today: UsageToday;
  monthly: UsageMonthly;
  limits: UsageLimits;
  features: PlanFeatures;
}

interface SubscriptionContextType {
  subscription: SubscriptionData | null;
  usage: UsageData | null;
  loading: boolean;
  error: string | null;
  refreshSubscription: () => Promise<void>;
  refreshUsage: () => Promise<void>;
  /** Quick check: can user perform this action? */
  canPerformAction: (action: 'questions' | 'drafts' | 'deadlines') => boolean;
  /** Quick check: is model mode allowed? */
  isModelModeAllowed: (mode: string) => boolean;
  /** Get remaining count for an action (-1 = unlimited) */
  getRemainingCount: (action: 'questions' | 'drafts' | 'deadlines') => number;
}

const SubscriptionContext = createContext<SubscriptionContextType>({
  subscription: null,
  usage: null,
  loading: true,
  error: null,
  refreshSubscription: async () => {},
  refreshUsage: async () => {},
  canPerformAction: () => true,
  isModelModeAllowed: () => true,
  getRemainingCount: () => -1,
});

const DEFAULT_LIMITS: UsageLimits = {
  questions_per_day: 3,
  questions_per_month: 30,
  drafts_per_month: 1,
  deadlines_per_month: 3,
  conversations: 5,
};

const DEFAULT_FEATURES: PlanFeatures = {
  model_modes: ['1.1'],
  pdf_export: false,
};

export function SubscriptionProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshSubscription = useCallback(async () => {
    if (!user) return;
    try {
      const data = await getSubscription();
      setSubscription(data);
      setError(null);
    } catch (e: any) {
      console.error('Failed to fetch subscription:', e);
      setError(e.message);
    }
  }, [user]);

  const refreshUsage = useCallback(async () => {
    if (!user) return;
    try {
      const data = await getUsage();
      setUsage(data);
    } catch (e: any) {
      console.error('Failed to fetch usage:', e);
    }
  }, [user]);

  // Fetch subscription and usage when user changes
  useEffect(() => {
    if (!user) {
      setSubscription(null);
      setUsage(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    Promise.all([refreshSubscription(), refreshUsage()])
      .finally(() => setLoading(false));
  }, [user, refreshSubscription, refreshUsage]);

  // Refresh usage every 5 minutes
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(refreshUsage, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [user, refreshUsage]);

  const canPerformAction = useCallback((action: 'questions' | 'drafts' | 'deadlines'): boolean => {
    if (!usage) return true; // Allow while loading

    const limits = usage.limits || DEFAULT_LIMITS;

    if (action === 'questions') {
      const dailyLimit = limits.questions_per_day;
      const monthlyLimit = limits.questions_per_month;
      if (dailyLimit !== -1 && usage.today.questions_count >= dailyLimit) return false;
      if (monthlyLimit !== -1 && usage.monthly.questions >= monthlyLimit) return false;
    } else if (action === 'drafts') {
      const monthlyLimit = limits.drafts_per_month;
      if (monthlyLimit !== -1 && usage.monthly.drafts >= monthlyLimit) return false;
    } else if (action === 'deadlines') {
      const monthlyLimit = limits.deadlines_per_month;
      if (monthlyLimit !== -1 && usage.monthly.deadlines >= monthlyLimit) return false;
    }

    return true;
  }, [usage]);

  const isModelModeAllowed = useCallback((mode: string): boolean => {
    const features = subscription?.features || usage?.features || DEFAULT_FEATURES;
    return features.model_modes.includes(mode);
  }, [subscription, usage]);

  const getRemainingCount = useCallback((action: 'questions' | 'drafts' | 'deadlines'): number => {
    if (!usage) return -1;

    const limits = usage.limits || DEFAULT_LIMITS;

    if (action === 'questions') {
      const dailyLimit = limits.questions_per_day;
      const monthlyLimit = limits.questions_per_month;
      if (dailyLimit === -1 && monthlyLimit === -1) return -1;

      const dailyRemaining = dailyLimit === -1 ? Infinity : Math.max(0, dailyLimit - usage.today.questions_count);
      const monthlyRemaining = monthlyLimit === -1 ? Infinity : Math.max(0, monthlyLimit - usage.monthly.questions);
      return Math.min(dailyRemaining, monthlyRemaining);
    } else if (action === 'drafts') {
      const limit = limits.drafts_per_month;
      return limit === -1 ? -1 : Math.max(0, limit - usage.monthly.drafts);
    } else if (action === 'deadlines') {
      const limit = limits.deadlines_per_month;
      return limit === -1 ? -1 : Math.max(0, limit - usage.monthly.deadlines);
    }

    return -1;
  }, [usage]);

  return (
    <SubscriptionContext.Provider
      value={{
        subscription,
        usage,
        loading,
        error,
        refreshSubscription,
        refreshUsage,
        canPerformAction,
        isModelModeAllowed,
        getRemainingCount,
      }}
    >
      {children}
    </SubscriptionContext.Provider>
  );
}

export const useSubscription = () => useContext(SubscriptionContext);
