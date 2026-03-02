'use client';

import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import { predictVerdictStreaming } from '@/lib/api';
import { useSubscription } from '@/lib/supabase/subscription-context';

const CASE_TYPES = [
  { value: '', label: 'اختر نوع القضية (اختياري)' },
  { value: 'طلاق', label: 'طلاق' },
  { value: 'حضانة', label: 'حضانة' },
  { value: 'نفقة', label: 'نفقة' },
  { value: 'إرث', label: 'إرث / ميراث' },
  { value: 'زيارة', label: 'زيارة' },
  { value: 'خلع', label: 'خلع' },
  { value: 'بيع', label: 'بيع' },
  { value: 'إيجار', label: 'إيجار' },
  { value: 'مقاولة', label: 'مقاولة' },
  { value: 'عمل', label: 'عمل' },
  { value: 'تعويض', label: 'تعويض' },
  { value: 'دين', label: 'دين / مطالبة مالية' },
  { value: 'منازعة تجارية', label: 'منازعة تجارية' },
  { value: 'شركات', label: 'شركات' },
  { value: 'إفلاس', label: 'إفلاس' },
  { value: 'ملكية فكرية', label: 'ملكية فكرية' },
];

export default function VerdictPredictionPage() {
  const { subscription, loading: subLoading } = useSubscription();
  const [caseType, setCaseType] = useState('');
  const [caseDetails, setCaseDetails] = useState('');
  const [prediction, setPrediction] = useState('');
  const [detectedCaseType, setDetectedCaseType] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const predictionRef = useRef('');
  const abortRef = useRef<AbortController | null>(null);

  const handlePredict = async () => {
    if (!caseDetails.trim()) {
      setError('يرجى إدخال تفاصيل القضية');
      return;
    }

    if (caseDetails.trim().length < 50) {
      setError('يرجى إدخال تفاصيل أكثر عن القضية (50 حرف على الأقل)');
      return;
    }

    setLoading(true);
    setError('');
    setPrediction('');
    setDetectedCaseType('');
    predictionRef.current = '';

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await predictVerdictStreaming(
        {
          case_type: caseType || undefined,
          case_details: caseDetails,
        },
        {
          onMeta: (data) => {
            setDetectedCaseType(data.case_type);
          },
          onToken: (text) => {
            predictionRef.current += text;
            setPrediction(predictionRef.current);
          },
          onDone: () => {
            setLoading(false);
          },
          onError: (err) => {
            setError(err);
            setLoading(false);
          },
        },
        controller
      );
    } catch {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const handleClear = () => {
    setCaseType('');
    setCaseDetails('');
    setPrediction('');
    setDetectedCaseType('');
    setError('');
  };

  // Loading subscription state
  if (subLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    );
  }

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
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center shadow-sm">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold gradient-text font-heading">توقع الحكم</h1>
            <p className="text-gray-500 text-sm">أدخل تفاصيل القضية واحصل على تنبؤ بالحكم المتوقع مبني على الأنظمة السعودية</p>
          </div>
        </div>
      </motion.div>

      {/* Input Form */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="glass-card p-4 sm:p-5 mb-5"
      >
        {/* Case Type Dropdown */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">نوع القضية</label>
          <select
            value={caseType}
            onChange={(e) => setCaseType(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 transition-all"
            dir="rtl"
          >
            {CASE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">إذا لم تختر، سيتم الكشف تلقائياً من تفاصيل القضية</p>
        </div>

        {/* Case Details Textarea */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">تفاصيل القضية</label>
          <textarea
            value={caseDetails}
            onChange={(e) => setCaseDetails(e.target.value)}
            rows={8}
            className="w-full px-4 py-3 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 resize-none transition-all leading-relaxed"
            placeholder={"اكتب تفاصيل القضية هنا...\n\nمثال:\n- الأطراف: الزوج والزوجة\n- الوقائع: رفعت الزوجة دعوى خلع بعد 3 سنوات زواج\n- الأدلة: عقد الزواج، شهادة شهود على الخلاف\n- المطالب: الخلع مع التنازل عن المؤخر"}
            dir="rtl"
          />
          <div className="flex justify-between mt-1">
            <p className="text-xs text-gray-400">كلما كانت التفاصيل أدق، كان التوقع أفضل</p>
            <p className={clsx('text-xs', caseDetails.length < 50 ? 'text-gray-400' : 'text-green-500')}>
              {caseDetails.length} حرف
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={loading ? handleCancel : handlePredict}
            disabled={loading ? false : !caseDetails.trim() || caseDetails.trim().length < 50}
            className={clsx(
              'flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-300',
              loading
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-gradient-to-l from-purple-500 to-purple-600 text-white hover:shadow-glow active:scale-[0.99] disabled:opacity-50'
            )}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                جاري التحليل... (اضغط للإلغاء)
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
                </svg>
                توقع الحكم
              </span>
            )}
          </button>
          {(prediction || caseDetails) && !loading && (
            <button
              onClick={handleClear}
              className="px-4 py-3 rounded-xl text-gray-500 border border-gray-200/80 hover:bg-gray-50 transition-all"
              title="مسح الكل"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </motion.div>

      {/* Error */}
      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-50/80 backdrop-blur-sm border border-red-200/50 rounded-xl p-4 mb-5 text-sm text-red-700"
        >
          {error}
        </motion.div>
      )}

      {/* Case Type Badge */}
      {detectedCaseType && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex items-center gap-2 mb-4"
        >
          <span className="text-xs font-medium text-gray-500">نوع القضية:</span>
          <span className="px-3 py-1 bg-purple-50/80 text-purple-700 rounded-lg text-sm font-medium border border-purple-200/50">
            {detectedCaseType}
          </span>
        </motion.div>
      )}

      {/* Prediction Result */}
      {prediction && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4 sm:p-6"
        >
          <div className="flex items-center justify-between mb-4 gap-2">
            <h3 className="font-bold gradient-text font-heading">تقرير التوقع:</h3>
            <div className="flex gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(prediction)}
                className="flex items-center gap-1.5 px-3 sm:px-4 py-1.5 text-xs bg-gray-100/80 text-gray-600 rounded-lg hover:bg-purple-50 hover:text-purple-600 transition-all"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                نسخ
              </button>
              <button
                onClick={() => {
                  const w = window.open('', '_blank');
                  if (w) {
                    w.document.write(`<html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>توقع حكم — سند</title><style>body{font-family:'Noto Naskh Arabic','Traditional Arabic',serif;padding:40px;line-height:2;font-size:16px;color:#1a1a2e}h1,h2,h3{color:#7c3aed}table{width:100%;border-collapse:collapse;margin:16px 0}th,td{border:1px solid #ddd;padding:8px 12px;text-align:right}th{background:#f5f3ff}blockquote{border-right:4px solid #7c3aed;padding-right:16px;margin:12px 0;color:#555;background:#f5f3ff;padding:8px 16px;border-radius:0 8px 8px 0}</style></head><body>${prediction.replace(/\n/g, '<br>')}</body></html>`);
                    w.document.close();
                    w.print();
                  }
                }}
                className="flex items-center gap-1.5 px-3 sm:px-4 py-1.5 text-xs bg-gray-100/80 text-gray-600 rounded-lg hover:bg-purple-50 hover:text-purple-600 transition-all"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                طباعة
              </button>
            </div>
          </div>
          <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed border-t border-gray-100/80 pt-4 font-legal">
            <ReactMarkdown>{prediction}</ReactMarkdown>
          </div>
          {loading && (
            <div className="flex items-center gap-2 mt-4 text-purple-600 text-sm">
              <div className="animate-pulse w-2 h-2 rounded-full bg-purple-500" />
              جاري التحليل...
            </div>
          )}

          {/* Disclaimer */}
          {!loading && prediction && (
            <div className="mt-6 p-3 bg-amber-50/80 border border-amber-200/50 rounded-xl text-xs text-amber-800 leading-relaxed">
              <div className="flex items-start gap-2">
                <svg className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <p>
                  <strong>تنبيه مهم:</strong> هذا تحليل تنبؤي أولي يعتمد على المعلومات المقدمة والأنظمة المرعية، ولا يُعد حكماً قضائياً ولا يُغني عن استشارة محامٍ مرخص. النتيجة الفعلية تعتمد على اجتهاد القاضي والأدلة المقدمة.
                </p>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
