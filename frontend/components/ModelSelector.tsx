'use client';

import { motion } from 'framer-motion';
import clsx from 'clsx';

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
  return (
    <div className="flex items-center bg-gray-100/80 rounded-xl p-1 gap-0.5">
      {MODELS.map((m) => (
        <button
          key={m.id}
          onClick={() => onChange(m.id)}
          disabled={disabled}
          className={clsx(
            'relative flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-300 whitespace-nowrap',
            value === m.id
              ? 'text-primary-700'
              : 'text-gray-400 hover:text-gray-600',
            disabled && 'opacity-50 cursor-not-allowed'
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
        </button>
      ))}
    </div>
  );
}
