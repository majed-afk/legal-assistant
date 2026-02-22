'use client';

import { useState, useEffect } from 'react';
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
      <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-2">📝 صياغة المذكرات</h1>
      <p className="text-gray-500 text-sm mb-4 sm:mb-6">صياغة مذكرات قانونية مبنية على نظام الأحوال الشخصية</p>

      {/* Draft type selection */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 sm:p-5 mb-4 sm:mb-6">
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
              className={`p-3 rounded-lg border text-sm text-right transition-colors ${
                selectedType === t.type
                  ? 'bg-primary-50 border-primary-300 text-primary-700'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {t.name_ar}
            </button>
          ))}
        </div>
      </div>

      {/* Form fields */}
      {currentType && (
        <div className="bg-white rounded-xl border border-gray-200 p-3 sm:p-5 mb-4 sm:mb-6">
          <h3 className="font-medium text-gray-700 mb-4">بيانات {currentType.name_ar}:</h3>
          <div className="space-y-4">
            {currentType.required_fields.map((field) => (
              <div key={field}>
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  {FIELD_LABELS[field] || field} *
                </label>
                {['facts', 'arguments', 'requests', 'reasons', 'appeal_grounds', 'response_to'].includes(field) ? (
                  <textarea
                    value={fields[field] || ''}
                    onChange={(e) => setFields({ ...fields, [field]: e.target.value })}
                    rows={4}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                    placeholder={`أدخل ${FIELD_LABELS[field] || field}...`}
                  />
                ) : (
                  <input
                    type="text"
                    value={fields[field] || ''}
                    onChange={(e) => setFields({ ...fields, [field]: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder={`أدخل ${FIELD_LABELS[field] || field}...`}
                  />
                )}
              </div>
            ))}
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'جاري الصياغة...' : 'صياغة المذكرة'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4 gap-2">
            <h3 className="font-bold text-gray-800">المذكرة المُعَدّة:</h3>
            <div className="flex gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(result)}
                className="px-3 sm:px-4 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
              >
                نسخ
              </button>
              <button
                onClick={() => {
                  const w = window.open('', '_blank');
                  if (w) {
                    w.document.write(`<html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>مذكرة قانونية</title><style>body{font-family:'Noto Naskh Arabic','Traditional Arabic',serif;padding:40px;line-height:2;font-size:16px;color:#1a1a2e}h1,h2,h3{color:#044889}</style></head><body>${result.replace(/\n/g,'<br>')}</body></html>`);
                    w.document.close();
                    w.print();
                  }
                }}
                className="px-3 sm:px-4 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
              >
                طباعة
              </button>
            </div>
          </div>
          <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed border-t border-gray-100 pt-4">
            <ReactMarkdown>{result}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
