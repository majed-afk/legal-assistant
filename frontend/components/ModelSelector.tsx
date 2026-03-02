'use client';

import { motion } from 'framer-motion';
import clsx from 'clsx';
import { useSubscription } from '@/lib/supabase/subscription-context';

interface Props {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}

const MODELS = [
  { id: '2.1', name: '\u0633\u0646\u062f 2.1', label: '\u0645\u0641\u0635\u0651\u0644', icon: '\uD83D\uDD0D' },
  { id: '1.1', name: '\u0633\u0646\u062f 1.1', label: '\u0633\u0631\u064a\u0639', icon: '\u26A1' },
];

export default function ModelSelector({ value, onChange, disabled }: Props) {
  const { isModelModeAllowed, isModelModeAvailable, getModelModeTrial } = useSubscription();

  return (
    <div className="flex items-center bg-gray-100/80 dark:bg-surface-900/80 rounded-xl p-1 gap-0.5">
      {MODELS.map((m) => {
        const inPlan = isModelModeAllowed(m.id);
        const available = isModelModeAvailable(m.id);
        const trial = m.id === '2.1' ? getModelModeTrial() : null;
        const isLocked = !available;
        const isTrial = !inPlan && available && trial !== null;

        return (
          <div key={m.id} className="relative group">
            <button
              onClick={() => {
                if (available) onChange(m.id);
              }}
              disabled={disabled || isLocked}
              className={clsx(
                'relative flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-300 whitespace-nowrap',
                value === m.id
                  ? 'text-primary-700 dark:text-primary-300'
                  : isLocked
                  ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                  : 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300',
                (disabled || isLocked) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {value === m.id && (
                <motion.div
                  layoutId="model-pill"
                  className="absolute inset-0 bg-white dark:bg-surface-800 rounded-lg shadow-sm"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative z-10">{m.icon}</span>
              <span className="relative z-10">{m.name}</span>
              {value === m.id && (
                <span className={clsx(
                  'relative z-10 text-[10px] px-1.5 py-0.5 rounded-full',
                  m.id === '2.1' ? 'bg-primary-100 text-primary-600' : 'bg-amber-100 text-amber-700'
                )}>
                  {m.label}
                </span>
              )}
              {/* Trial badge for free users with remaining trials */}
              {isTrial && trial && (
                <span className="relative z-10 text-[9px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-bold">
                  {trial.remaining} \u062a\u062c\u0631\u0628\u0629
                </span>
              )}
              {/* Lock icon for fully locked mode */}
              {isLocked && (
                <svg className="relative z-10 w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              )}
            </button>

            {/* Tooltip for trial mode */}
            {isTrial && trial && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-800 text-white text-[10px] rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                \u0628\u0642\u064a \u0644\u0643 {trial.remaining} \u062a\u062c\u0631\u0628\u0629 \u0645\u062c\u0627\u0646\u064a\u0629 \u0645\u0646 \u0623\u0635\u0644 {trial.max}
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
              </div>
            )}

            {/* Tooltip for fully locked mode */}
            {isLocked && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-800 text-white text-[10px] rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                {trial && trial.remaining === 0
                  ? '\u0627\u0646\u062a\u0647\u062a \u0627\u0644\u062a\u062c\u0627\u0631\u0628 \u0627\u0644\u0645\u062c\u0627\u0646\u064a\u0629 \u2014 \u062a\u0631\u0642\u0651\u064E \u0644\u0644\u0628\u0627\u0642\u0629 \u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0629'
                  : '\u0645\u062a\u0627\u062d \u0641\u064a \u0627\u0644\u0628\u0627\u0642\u0629 \u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0629 \u0648\u0623\u0639\u0644\u0649'}
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
