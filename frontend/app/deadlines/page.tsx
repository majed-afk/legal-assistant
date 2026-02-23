'use client';

import { useState } from 'react';
import { calculateDeadline } from '@/lib/api';

const EVENT_TYPES = [
  { type: 'divorce', name: 'طلاق', icon: '💔', description: 'حساب عدة الطلاق ومهل المراجعة' },
  { type: 'death', name: 'وفاة', icon: '🕊️', description: 'حساب عدة الوفاة' },
  { type: 'judgment', name: 'حكم قضائي', icon: '⚖️', description: 'حساب مهل الاعتراض' },
  { type: 'custody', name: 'حضانة', icon: '👶', description: 'مواعيد متعلقة بالحضانة' },
  { type: 'appeal', name: 'استئناف', icon: '📋', description: 'حساب مهل الاستئناف والنقض' },
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
      <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-2">⏰ حاسبة المهل النظامية</h1>
      <p className="text-gray-500 text-sm mb-4 sm:mb-6">احسب المواعيد والمهل القانونية وفق الأنظمة السعودية</p>

      {/* Event type selection */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 sm:p-5 mb-4 sm:mb-6">
        <h3 className="font-medium text-gray-700 mb-3">نوع الحدث:</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 sm:gap-3">
          {EVENT_TYPES.map((et) => (
            <button
              key={et.type}
              onClick={() => {
                setEventType(et.type);
                setResult(null);
              }}
              className={`p-3 rounded-lg border text-right transition-colors ${
                eventType === et.type
                  ? 'bg-primary-50 border-primary-300'
                  : 'border-gray-200 hover:bg-gray-50'
              }`}
            >
              <span className="text-lg ml-2">{et.icon}</span>
              <span className="text-sm font-medium">{et.name}</span>
              <p className="text-xs text-gray-500 mt-1">{et.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Date and details */}
      {eventType && (
        <div className="bg-white rounded-xl border border-gray-200 p-3 sm:p-5 mb-4 sm:mb-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">تاريخ الحدث (ميلادي):</label>
              <input
                type="date"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {['divorce', 'death'].includes(eventType) && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isPregnant}
                  onChange={(e) => setIsPregnant(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded"
                />
                <span className="text-sm text-gray-700">المرأة حامل</span>
              </label>
            )}

            {eventType === 'divorce' && (
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">نوع الطلاق:</label>
                <select
                  value={divorceType}
                  onChange={(e) => setDivorceType(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="revocable">رجعي</option>
                  <option value="irrevocable">بائن</option>
                </select>
              </div>
            )}

            {eventType === 'custody' && (
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">عمر الطفل (سنوات):</label>
                <input
                  type="number"
                  min={0}
                  max={18}
                  value={childAge}
                  onChange={(e) => setChildAge(Number(e.target.value))}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm"
                />
              </div>
            )}

            <button
              onClick={handleCalculate}
              disabled={loading || !eventDate}
              className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? 'جاري الحساب...' : 'احسب المهل'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700">{error}</div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {result.deadlines.map((dl, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-3 sm:p-5">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-lg font-bold flex-shrink-0">
                  {i + 1}
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-gray-800">{dl.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{dl.description}</p>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs">
                    <span className="px-2 py-1 bg-red-50 text-red-700 rounded">
                      ينتهي: {dl.end_date}
                      {dl.approximate && ' (تقريبي)'}
                    </span>
                    <span className="px-2 py-1 bg-gray-50 text-gray-600 rounded">
                      السند: {dl.legal_basis}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {result.notes.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <h4 className="font-medium text-amber-800 mb-2">ملاحظات مهمة:</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-amber-700">
                {result.notes.map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
