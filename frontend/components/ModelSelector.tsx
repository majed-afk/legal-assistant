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
  { id: '2.1', name: 'سند 2.1', label: 'مفصّل', icon: '🔍' },
  { id: '1.1', name: 'سند 1.1', label: 'سريع', icon: '⚡' },
];

export default function ModelSelector({ value, onChange, disabled }: Props) {
  const { isModelModeAllowed, subscription } = useSubscription();

  return (
    <div className="flex items-center bg-gray-100/80 rounded-xl p-1 gap-0.5">
      {MODELS.map((m) => {
        const allowed = isModelModeAllowed(m.id);
        const isLocked = !allowed;

        return (
          <div key={m.id} className="relative group">
            <button
              onClick={() => {
                if (allowed) onChange(m.id);
              }}
              disabled={disabled || isLocked}
              className={clsx(
                'relative flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-300 whitespace-nowrap',
                value === m.id
                  ? 'text-primary-700'
                  : isLocked
                  ? 'text-gray-300 cursor-not-allowed'
                  : 'text-gray-400 hover:text-gray-600',
                (disabled || isLocked) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {value === m.id && (
                <motion.div
                  layoutId="model-pill"
                  className="absolute inset-0 bg-white rounded-lg shadow-sm"
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
              {isLocked && (
                <svg className="relative z-10 w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              )}
            </button>

            {/* Tooltip for locked mode */}
            {isLocked && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-800 text-white text-[10px] rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                متاح في الباقة الأساسية وأعلى
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
