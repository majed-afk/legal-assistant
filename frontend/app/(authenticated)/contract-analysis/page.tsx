'use client';

import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import { analyzeContractStreaming } from '@/lib/api';
import { useSubscription } from '@/lib/supabase/subscription-context';

export default function ContractAnalysisPage() {
  const { subscription, loading: subLoading } = useSubscription();
  const [inputMode, setInputMode] = useState<'file' | 'text'>('file');
  const [file, setFile] = useState<File | null>(null);
  const [contractText, setContractText] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [contractType, setContractType] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const analysisRef = useRef('');
  const abortRef = useRef<AbortController | null>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isValidFile(droppedFile)) {
      setFile(droppedFile);
      setError('');
    } else {
      setError('يرجى رفع ملف PDF أو DOCX فقط');
    }
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && isValidFile(selected)) {
      setFile(selected);
      setError('');
    } else if (selected) {
      setError('يرجى رفع ملف PDF أو DOCX فقط');
    }
  }, []);

  const isValidFile = (f: File) => {
    return f.type === 'application/pdf' ||
      f.name.endsWith('.docx') ||
      f.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  };

  const handleAnalyze = async () => {
    const hasInput = inputMode === 'file' ? file : contractText.trim();
    if (!hasInput) {
      setError(inputMode === 'file' ? 'يرجى رفع ملف العقد' : 'يرجى لصق نص العقد');
      return;
    }

    setLoading(true);
    setError('');
    setAnalysis('');
    setContractType('');
    analysisRef.current = '';

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await analyzeContractStreaming(
        inputMode === 'file' ? { file: file! } : { text: contractText },
        {
          onMeta: (data) => {
            setContractType(data.contract_type);
          },
          onToken: (text) => {
            analysisRef.current += text;
            setAnalysis(analysisRef.current);
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
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold gradient-text font-heading">تحليل العقود</h1>
            <p className="text-gray-500 text-sm">حلّل عقودك مقابل الأنظمة السعودية واكتشف المخاطر والتوصيات</p>
          </div>
        </div>
      </motion.div>

      {/* Input Mode Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="glass-card p-4 sm:p-5 mb-5"
      >
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setInputMode('file')}
            className={clsx(
              'flex-1 py-2.5 px-4 rounded-xl text-sm font-medium transition-all duration-300',
              inputMode === 'file'
                ? 'bg-primary-50/80 border border-primary-300 text-primary-700 shadow-sm'
                : 'border border-gray-200/80 text-gray-500 hover:bg-white hover:shadow-elevated'
            )}
          >
            <span className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              رفع ملف
            </span>
          </button>
          <button
            onClick={() => setInputMode('text')}
            className={clsx(
              'flex-1 py-2.5 px-4 rounded-xl text-sm font-medium transition-all duration-300',
              inputMode === 'text'
                ? 'bg-primary-50/80 border border-primary-300 text-primary-700 shadow-sm'
                : 'border border-gray-200/80 text-gray-500 hover:bg-white hover:shadow-elevated'
            )}
          >
            <span className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              لصق نص
            </span>
          </button>
        </div>

        {/* File Upload */}
        {inputMode === 'file' && (
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onClick={() => fileInputRef.current?.click()}
            className={clsx(
              'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300',
              isDragging
                ? 'border-primary-400 bg-primary-50/50'
                : file
                  ? 'border-green-300 bg-green-50/30'
                  : 'border-gray-200/80 hover:border-primary-300 hover:bg-primary-50/20'
            )}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileChange}
              className="hidden"
            />
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <svg className="w-10 h-10 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm font-medium text-gray-700">{file.name}</p>
                <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(0)} KB</p>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="text-xs text-red-500 hover:text-red-700 mt-1"
                >
                  إزالة الملف
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <svg className="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <div>
                  <p className="text-sm text-gray-500">اسحب الملف هنا أو <span className="text-primary-600 font-medium">اضغط للاختيار</span></p>
                  <p className="text-xs text-gray-400 mt-1">PDF أو DOCX — حد أقصى 5 ميجا</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Text Input */}
        {inputMode === 'text' && (
          <textarea
            value={contractText}
            onChange={(e) => setContractText(e.target.value)}
            rows={10}
            className="w-full px-4 py-3 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 resize-none transition-all leading-relaxed"
            placeholder="الصق نص العقد هنا..."
            dir="rtl"
          />
        )}

        {/* Analyze Button */}
        <button
          onClick={loading ? handleCancel : handleAnalyze}
          disabled={loading ? false : (inputMode === 'file' ? !file : !contractText.trim())}
          className={clsx(
            'w-full mt-4 px-6 py-3 rounded-xl font-medium transition-all duration-300',
            loading
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-gradient-to-l from-primary-500 to-primary-600 text-white hover:shadow-glow active:scale-[0.99] disabled:opacity-50'
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
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              تحليل العقد
            </span>
          )}
        </button>
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

      {/* Contract Type Badge */}
      {contractType && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex items-center gap-2 mb-4"
        >
          <span className="text-xs font-medium text-gray-500">نوع العقد المُكتشف:</span>
          <span className="px-3 py-1 bg-primary-50/80 text-primary-700 rounded-lg text-sm font-medium border border-primary-200/50">
            عقد {contractType}
          </span>
        </motion.div>
      )}

      {/* Analysis Result */}
      {analysis && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4 sm:p-6"
        >
          <div className="flex items-center justify-between mb-4 gap-2">
            <h3 className="font-bold gradient-text font-heading">تقرير التحليل:</h3>
            <div className="flex gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(analysis)}
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
                    w.document.write(`<html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>تحليل عقد — سند</title><style>body{font-family:'Noto Naskh Arabic','Traditional Arabic',serif;padding:40px;line-height:2;font-size:16px;color:#1a1a2e}h1,h2,h3{color:#4338ca}blockquote{border-right:4px solid #c49a38;padding-right:16px;margin:12px 0;color:#555;background:#fffbf0;padding:8px 16px;border-radius:0 8px 8px 0}</style></head><body>${analysis.replace(/\n/g, '<br>')}</body></html>`);
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
            <ReactMarkdown>{analysis}</ReactMarkdown>
          </div>
          {loading && (
            <div className="flex items-center gap-2 mt-4 text-primary-600 text-sm">
              <div className="animate-pulse w-2 h-2 rounded-full bg-primary-500" />
              جاري التحليل...
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
