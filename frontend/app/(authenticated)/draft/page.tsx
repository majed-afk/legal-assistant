'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { draftDocument, getDraftTypes } from '@/lib/api';
import ReactMarkdown from 'react-markdown';

interface DraftType {
  type: string;
  name_ar: string;
  required_fields: string[];
}

const FIELD_LABELS: Record<string, string> = {
  plaintiff_name: 'اسم المدعي',
  defendant_name: 'اسم المدعى عليه',
  case_type: 'نوع القضية',
  facts: 'وقائع القضية',
  requests: 'الطلبات',
  case_number: 'رقم القضية',
  arguments: 'الحجج والأسانيد',
  judgment_number: 'رقم الحكم',
  judgment_date: 'تاريخ الحكم',
  appeal_grounds: 'أسباب الاعتراض',
  response_to: 'الرد على',
  wife_name: 'اسم الزوجة',
  husband_name: 'اسم الزوج',
  reasons: 'الأسباب',
  compensation_offer: 'العوض المقدم',
  parent_name: 'اسم الوالد/ة طالب الحضانة',
  children_names: 'أسماء الأطفال',
  children_ages: 'أعمار الأطفال',
  claimant_name: 'اسم المطالب',
  relationship: 'صلة القرابة',
  amount_requested: 'المبلغ المطلوب',
};

export default function DraftPage() {
  const [draftTypes, setDraftTypes] = useState<DraftType[]>([]);
  const [selectedType, setSelectedType] = useState('');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getDraftTypes()
      .then((data) => setDraftTypes(data.types))
      .catch(() => {});
  }, []);

  const currentType = draftTypes.find((t) => t.type === selectedType);

  const handleSubmit = async () => {
    if (!selectedType) return;
    setLoading(true);
    setError('');
    setResult('');
    try {
      const data = await draftDocument(selectedType, fields);
      setResult(data.draft);
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
              <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold gradient-text font-heading">صياغة المذكرات</h1>
            <p className="text-gray-500 text-sm">صياغة مذكرات قانونية مبنية على الأنظمة السعودية</p>
          </div>
        </div>
      </motion.div>

      {/* Draft type selection */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="glass-card p-4 sm:p-5 mb-5"
      >
        <h3 className="font-medium text-gray-700 mb-3">اختر نوع المذكرة:</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 sm:gap-3">
          {draftTypes.map((t) => (
            <button
              key={t.type}
              onClick={() => {
                setSelectedType(t.type);
                setFields({});
                setResult('');
              }}
              className={clsx(
                'p-3.5 rounded-xl border text-sm text-right transition-all duration-300',
                selectedType === t.type
                  ? 'bg-primary-50/80 border-primary-300 text-primary-700 shadow-sm'
                  : 'border-gray-200/80 text-gray-600 hover:bg-white hover:shadow-elevated hover:-translate-y-0.5'
              )}
            >
              {t.name_ar}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Form fields */}
      {currentType && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="glass-card p-4 sm:p-5 mb-5"
        >
          <h3 className="font-medium text-gray-700 mb-4">بيانات {currentType.name_ar}:</h3>
          <div className="space-y-4">
            {currentType.required_fields.map((field) => (
              <div key={field}>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">
                  {FIELD_LABELS[field] || field} *
                </label>
                {['facts', 'arguments', 'requests', 'reasons', 'appeal_grounds', 'response_to'].includes(field) ? (
                  <textarea
                    value={fields[field] || ''}
                    onChange={(e) => setFields({ ...fields, [field]: e.target.value })}
                    rows={4}
                    className="w-full px-4 py-2.5 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 resize-none transition-all"
                    placeholder={`أدخل ${FIELD_LABELS[field] || field}...`}
                  />
                ) : (
                  <input
                    type="text"
                    value={fields[field] || ''}
                    onChange={(e) => setFields({ ...fields, [field]: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 transition-all"
                    placeholder={`أدخل ${FIELD_LABELS[field] || field}...`}
                  />
                )}
              </div>
            ))}
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full px-6 py-3 bg-gradient-to-l from-primary-500 to-primary-600 text-white rounded-xl font-medium hover:shadow-glow active:scale-[0.99] disabled:opacity-50 transition-all duration-300"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  جاري الصياغة...
                </span>
              ) : 'صياغة المذكرة'}
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

      {/* Result */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4 sm:p-6"
        >
          <div className="flex items-center justify-between mb-4 gap-2">
            <h3 className="font-bold gradient-text font-heading">المذكرة المُعَدّة:</h3>
            <div className="flex gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(result)}
                className="flex items-center gap-1.5 px-3 sm:px-4 py-1.5 text-xs bg-gray-100/80 text-gray-600 rounded-lg hover:bg-primary-50 hover:text-primary-600 transition-all"
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
                    w.document.write(`<html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>مذكرة قانونية — سند</title><style>body{font-family:'Noto Naskh Arabic','Traditional Arabic',serif;padding:40px;line-height:2;font-size:16px;color:#1a1a2e}h1,h2,h3{color:#4338ca}blockquote{border-right:4px solid #c49a38;padding-right:16px;margin:12px 0;color:#555;background:#fffbf0;padding:8px 16px;border-radius:0 8px 8px 0}</style></head><body>${result.replace(/\n/g,'<br>')}</body></html>`);
                    w.document.close();
                    w.print();
                  }
                }}
                className="flex items-center gap-1.5 px-3 sm:px-4 py-1.5 text-xs bg-gray-100/80 text-gray-600 rounded-lg hover:bg-primary-50 hover:text-primary-600 transition-all"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                طباعة
              </button>
            </div>
          </div>
          <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed border-t border-gray-100/80 pt-4 font-legal">
            <ReactMarkdown>{result}</ReactMarkdown>
          </div>
        </motion.div>
      )}
    </div>
  );
}
