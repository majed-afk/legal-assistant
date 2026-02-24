'use client';

import { useState, useRef, useEffect } from 'react';

interface Props {
  value: string;
  onChange: (mode: string) => void;
  disabled?: boolean;
}

const models = [
  {
    id: '2.1',
    name: 'سند 2.1',
    label: 'مفصّل',
    description: 'تحليل شامل مع الأسانيد النظامية',
    icon: '🔍',
  },
  {
    id: '1.1',
    name: 'سند 1.1',
    label: 'سريع',
    description: 'إجابة مختصرة وسريعة',
    icon: '⚡',
  },
];

export default function ModelSelector({ value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selected = models.find((m) => m.id === value) || models[0];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors disabled:opacity-50"
      >
        <span>{selected.icon}</span>
        <span>{selected.name}</span>
        <svg className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-1 w-64 bg-white rounded-xl shadow-lg border border-gray-200 py-1 z-50">
          {models.map((m) => (
            <button
              key={m.id}
              onClick={() => {
                onChange(m.id);
                setOpen(false);
              }}
              className={`w-full flex items-start gap-3 px-4 py-3 text-right hover:bg-gray-50 transition-colors ${
                value === m.id ? 'bg-primary-50' : ''
              }`}
            >
              <span className="text-lg mt-0.5">{m.icon}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">{m.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                    m.id === '1.1'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-primary-100 text-primary-700'
                  }`}>
                    {m.label}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{m.description}</p>
              </div>
              {value === m.id && (
                <svg className="w-4 h-4 text-primary-600 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
