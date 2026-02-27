'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { trackEvent, EVENTS } from '@/lib/analytics';

interface Props {
  message: {
    id?: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: any[];
    classification?: any;
    isStreaming?: boolean;
    isError?: boolean;
  };
  conversationId?: string;
  isLastAssistant?: boolean;
  onRetry?: () => void;
  onRegenerate?: () => void;
}

export default function MessageBubble({ message, conversationId, isLastAssistant, onRetry, onRegenerate }: Props) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [codeCopied, setCodeCopied] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);
  const [feedbackSent, setFeedbackSent] = useState(false);

  const handleFeedback = async (rating: 'positive' | 'negative') => {
    if (feedbackSent) return;
    setFeedback(rating);
    setFeedbackSent(true);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://legal-assistant-55zm.onrender.com/api';
      await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: message.id || 'unknown',
          conversation_id: conversationId || 'unknown',
          rating,
        }),
      });
      trackEvent(EVENTS.FEEDBACK_GIVEN, {
        rating,
        message_id: message.id,
        conversation_id: conversationId,
      });
    } catch (e) {
      console.warn('Feedback error:', e);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCodeCopied(code);
    setTimeout(() => setCodeCopied(null), 2000);
  };

  const handlePrint = () => {
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="utf-8">
  <title>استشارة قانونية — سند</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Noto Naskh Arabic', 'Traditional Arabic', serif; padding: 40px 60px; line-height: 2.2; font-size: 15px; color: #1a1a2e; max-width: 800px; margin: 0 auto; }
    h1, h2, h3 { color: #4338ca; border-bottom: 1px solid #e0e7ff; padding-bottom: 4px; margin-top: 24px; }
    h2 { font-size: 18px; } h3 { font-size: 16px; }
    strong { color: #312e81; }
    ul, ol { padding-right: 20px; }
    li { margin-bottom: 4px; }
    blockquote { border-right: 4px solid #c49a38; padding-right: 16px; margin: 12px 0; color: #555; background: #fffbf0; padding: 8px 16px; border-radius: 0 8px 8px 0; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; }
    th, td { border: 1px solid #e0e7ff; padding: 8px 12px; text-align: right; }
    th { background: #f5f3ff; font-weight: 600; }
    .header { text-align: center; margin-bottom: 30px; padding-bottom: 16px; border-bottom: 2px solid #4338ca; }
    .header h1 { border: none; margin: 0; color: #4338ca; }
    .header p { color: #666; font-size: 13px; margin-top: 4px; }
    .footer { margin-top: 40px; padding-top: 16px; border-top: 2px solid #4338ca; font-size: 12px; color: #666; text-align: center; }
    @media print { body { padding: 20px; } }
  </style>
</head>
<body>
  <div class="header">
    <h1>Sanad AI — سند</h1>
    <p>استشارة قانونية - الأنظمة السعودية</p>
  </div>
  ${message.content.replace(/\n/g, '<br>').replace(/#{3}\s*(.+)/g, '<h3>$1</h3>').replace(/#{2}\s*(.+)/g, '<h2>$1</h2>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}
  <div class="footer">
    هذه استشارة قانونية أولية — لا تغني عن مراجعة محامٍ مرخص
  </div>
</body>
</html>`);
    w.document.close();
    w.print();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={isUser ? 'flex justify-start' : ''}
    >
      <div
        className={`group relative max-w-full rounded-2xl p-3.5 sm:p-4 transition-shadow duration-300 ${
          isUser
            ? 'bg-gradient-to-l from-primary-500 to-primary-600 text-white max-w-[90%] sm:max-w-[80%] shadow-md'
            : message.isError
              ? 'bg-red-50/80 backdrop-blur-sm border border-red-200/80 shadow-sm border-r-[3px] border-r-red-400'
              : 'bg-white/80 backdrop-blur-sm border border-gray-100/80 shadow-sm hover:shadow-elevated border-r-[3px] border-r-primary-400'
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : (
          <>
            {/* Copy & Print - appear on hover */}
            {!message.isStreaming && !message.isError && (
              <div className="absolute top-2.5 left-2.5 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 no-print">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-all"
                  title="نسخ"
                >
                  {copied ? (
                    <>
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>تم</span>
                    </>
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  )}
                </button>
                <button
                  onClick={handlePrint}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-all"
                  title="طباعة"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                  </svg>
                </button>
                <span className="w-px h-4 bg-gray-200 mx-0.5" />
                <button
                  onClick={() => handleFeedback('positive')}
                  className={`flex items-center gap-1 px-2 py-1 text-xs rounded-lg transition-all ${
                    feedback === 'positive'
                      ? 'text-green-600 bg-green-50'
                      : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                  }`}
                  title="إجابة مفيدة"
                  disabled={feedbackSent}
                >
                  <svg className="w-3.5 h-3.5" fill={feedback === 'positive' ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                </button>
                <button
                  onClick={() => handleFeedback('negative')}
                  className={`flex items-center gap-1 px-2 py-1 text-xs rounded-lg transition-all ${
                    feedback === 'negative'
                      ? 'text-red-500 bg-red-50'
                      : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
                  }`}
                  title="إجابة غير مفيدة"
                  disabled={feedbackSent}
                >
                  <svg className="w-3.5 h-3.5" fill={feedback === 'negative' ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                  </svg>
                </button>
              </div>
            )}

            <div className={`prose prose-sm max-w-none leading-relaxed font-legal ${message.isError ? 'text-red-700' : 'text-gray-800'}`}>
              <ReactMarkdown
                components={{
                  h2: ({ children }) => (
                    <h2 className="text-lg font-bold gradient-text mt-5 mb-2 border-b border-primary-100 pb-1.5 font-heading">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-bold text-primary-700 mt-4 mb-2 border-b border-gray-100 pb-1 font-heading">
                      {children}
                    </h3>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-gray-900">{children}</strong>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside space-y-1.5 my-2">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside space-y-1.5 my-2">{children}</ol>
                  ),
                  p: ({ children }) => (
                    <p className="my-2 leading-loose">{children}</p>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-r-4 border-gold-500 pr-4 my-3 text-gray-700 bg-gold-300/10 py-2.5 px-1 rounded-l-lg">
                      {children}
                    </blockquote>
                  ),
                  code: ({ className, children, ...props }) => {
                    const match = /language-(\w+)/.exec(className || '');
                    const codeString = String(children).replace(/\n$/, '');
                    const isInline = !match && !codeString.includes('\n');

                    if (isInline) {
                      return (
                        <code className="px-1.5 py-0.5 bg-primary-50 text-primary-700 rounded text-xs font-mono" {...props}>
                          {children}
                        </code>
                      );
                    }

                    return (
                      <div className="relative group/code my-3 rounded-xl overflow-hidden border border-gray-200/50">
                        <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-b border-gray-200/50">
                          <span className="text-[10px] text-gray-400 font-mono">{match?.[1] || 'code'}</span>
                          <button
                            onClick={() => handleCopyCode(codeString)}
                            className="text-[10px] text-gray-400 hover:text-primary-600 transition-colors"
                          >
                            {codeCopied === codeString ? 'تم النسخ' : 'نسخ'}
                          </button>
                        </div>
                        <pre className="p-3 overflow-x-auto bg-gray-50/50 text-xs leading-relaxed" dir="ltr">
                          <code className="font-mono text-gray-800" {...props}>
                            {children}
                          </code>
                        </pre>
                      </div>
                    );
                  },
                  table: ({ children }) => (
                    <div className="my-3 overflow-x-auto rounded-xl border border-gray-200/50">
                      <table className="w-full text-sm border-collapse">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-primary-50/50">{children}</thead>
                  ),
                  th: ({ children }) => (
                    <th className="px-3 py-2 text-right font-semibold text-primary-700 border-b border-gray-200/50 text-xs">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-3 py-2 text-right border-b border-gray-100/50 text-xs text-gray-700">
                      {children}
                    </td>
                  ),
                  tr: ({ children }) => (
                    <tr className="hover:bg-gray-50/50 transition-colors">{children}</tr>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.isStreaming && (
                <span className="inline-block w-1.5 h-5 rounded-full bg-gradient-to-b from-primary-400 to-primary-600 animate-pulse mr-1 align-text-bottom shadow-glow" />
              )}
            </div>

            {/* Error retry button */}
            {message.isError && onRetry && (
              <div className="mt-3 pt-3 border-t border-red-100/80">
                <button
                  onClick={onRetry}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs text-red-600 hover:bg-red-100/50 rounded-lg transition-all"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  أعد المحاولة
                </button>
              </div>
            )}

            {/* Regenerate button */}
            {onRegenerate && !message.isError && (
              <div className="mt-3 pt-3 border-t border-gray-100/80">
                <button
                  onClick={onRegenerate}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-all"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  أعد التوليد
                </button>
              </div>
            )}
          </>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100/80">
            <p className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              المصادر:
            </p>
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {message.sources.map((src: any, i: number) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-primary-50/80 text-primary-700 rounded-lg text-xs border border-primary-100/50"
                >
                  <svg className="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {src.chapter} - {src.topic}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Classification badge */}
        {message.classification && (
          <div className="mt-2.5 flex gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 bg-primary-50 text-primary-700 rounded-full text-xs border border-primary-100/50">
              {message.classification.category}
            </span>
            <span className="inline-flex items-center px-2.5 py-0.5 bg-gray-50 text-gray-500 rounded-full text-xs border border-gray-100">
              {message.classification.intent}
            </span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
