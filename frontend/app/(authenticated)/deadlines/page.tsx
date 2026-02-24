'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { calculateDeadline } from '@/lib/api';

const EVENT_TYPES = [
  { type: 'divorce', name: 'طلاق', icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z', description: 'حساب عدة الطلاق ومهل المراجعة' },
  { type: 'death', name: 'وفاة', icon: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z', description: 'حساب عدة الوفاة' },
  { type: 'judgment', name: 'حكم قضائي', icon: 'M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3', description: 'حساب مهل الاعتراض' },
  { type: 'custody', name: 'حضانة', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z', description: 'مواعيد متعلقة بالحضانة' },
  { type: 'appeal', name: 'استئناف', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', description: 'حساب مهل الاستئناف والنقض' },
];

interface Deadline {
  name: string;
  description: string;
  end_date: string;
  legal_basis: string;
  approximate?: boolean;
}

export default function DeadlinesPage() {
  const [eventType, setEventType] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [isPregnant, setIsPregnant] = useState(false);
  const [divorceType, setDivorceType] = useState('revocable');
  const [childAge, setChildAge] = useState(0);
  const [result, setResult] = useState<{ deadlines: Deadline[]; notes: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCalculate = async () => {
    if (!eventType || !eventDate) return;
    setLoading(true);
    setError('');
    setResult(null);

    const details: any = {};
    if (['divorce', 'death'].includes(eventType)) details.is_pregnant = isPregnant;
    if (eventType === 'divorce') details.divorce_type = divorceType;
    if (eventType === 'custody') details.child_age = childAge;

    try {
      const data = await calculateDeadline(eventType, eventDate, details);
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold gradient-text font-heading">حاسبة المهل النظامية</h1>
            <p className="text-gray-500 text-sm">احسب المواعيد والمهل القانونية وفق الأنظمة السعودية</p>
          </div>
        </div>
      </motion.div>

      {/* Event type selection */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="glass-card p-4 sm:p-5 mb-5"
      >
        <h3 className="font-medium text-gray-700 mb-3">نوع الحدث:</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 sm:gap-3">
          {EVENT_TYPES.map((et, i) => (
            <motion.button
              key={et.type}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.15 + i * 0.05 }}
              onClick={() => {
                setEventType(et.type);
                setResult(null);
              }}
              className={clsx(
                'p-3.5 rounded-xl border text-right transition-all duration-300 flex items-start gap-3',
                eventType === et.type
                  ? 'bg-primary-50/80 border-primary-300 shadow-sm'
                  : 'border-gray-200/80 hover:bg-white hover:shadow-elevated hover:-translate-y-0.5'
              )}
            >
              <div className={clsx(
                'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
                eventType === et.type ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-500'
              )}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={et.icon} />
                </svg>
              </div>
              <div>
                <span className="text-sm font-medium block">{et.name}</span>
                <p className="text-xs text-gray-500 mt-0.5">{et.description}</p>
              </div>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Date and details */}
      {eventType && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="glass-card p-4 sm:p-5 mb-5"
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">تاريخ الحدث (ميلادي):</label>
              <input
                type="date"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 transition-all"
              />
            </div>

            {['divorce', 'death'].includes(eventType) && (
              <label className="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition-colors">
                <input
                  type="checkbox"
                  checked={isPregnant}
                  onChange={(e) => setIsPregnant(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">المرأة حامل</span>
              </label>
            )}

            {eventType === 'divorce' && (
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">نوع الطلاق:</label>
                <select
                  value={divorceType}
                  onChange={(e) => setDivorceType(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 transition-all"
                >
                  <option value="revocable">رجعي</option>
                  <option value="irrevocable">بائن</option>
                </select>
              </div>
            )}

            {eventType === 'custody' && (
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">عمر الطفل (سنوات):</label>
                <input
                  type="number"
                  min={0}
                  max={18}
                  value={childAge}
                  onChange={(e) => setChildAge(Number(e.target.value))}
                  className="w-full px-4 py-2.5 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 transition-all"
                />
              </div>
            )}

            <button
              onClick={handleCalculate}
              disabled={loading || !eventDate}
              className="w-full px-6 py-3 bg-gradient-to-l from-primary-500 to-primary-600 text-white rounded-xl font-medium hover:shadow-glow active:scale-[0.99] disabled:opacity-50 transition-all duration-300"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  جاري الحساب...
                </span>
              ) : 'احسب المهل'}
            </button>
          </div>
        </motion.div>
      )}

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-50/80 backdrop-blur-sm border border-red-200/50 rounded-xl p-4 mb-5 text-sm text-red-700"
        >
          {error}
        </motion.div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {result.deadlines.map((dl, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.1 }}
              className="glass-card p-4 sm:p-5 hover:shadow-elevated transition-shadow duration-300"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 text-white flex items-center justify-center text-lg font-bold flex-shrink-0 shadow-sm">
                  {i + 1}
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-gray-800">{dl.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{dl.description}</p>
                  <div className="mt-2.5 flex flex-wrap gap-2.5 text-xs">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50/80 text-red-700 rounded-lg border border-red-100/50">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      ينتهي: {dl.end_date}
                      {dl.approximate && ' (تقريبي)'}
                    </span>
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-50/80 text-gray-600 rounded-lg border border-gray-100">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                      السند: {dl.legal_basis}
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}

          {result.notes.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-gold-300/10 border border-gold-400/20 rounded-xl p-4"
            >
              <h4 className="font-medium text-gold-700 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>
                ملاحظات مهمة:
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-gold-700/80">
                {result.notes.map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
              </ul>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
