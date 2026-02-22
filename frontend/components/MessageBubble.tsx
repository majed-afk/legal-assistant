'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

interface Props {
  message: {
    role: 'user' | 'assistant';
    content: string;
    sources?: any[];
    classification?: any;
    isStreaming?: boolean;
  };
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="utf-8">
  <title>استشارة قانونية</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Noto Naskh Arabic', 'Traditional Arabic', serif; padding: 40px 60px; line-height: 2.2; font-size: 15px; color: #1a1a2e; max-width: 800px; margin: 0 auto; }
    h1, h2, h3 { color: #044889; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-top: 24px; }
    h2 { font-size: 18px; } h3 { font-size: 16px; }
    strong { color: #0a3d71; }
    ul, ol { padding-right: 20px; }
    li { margin-bottom: 4px; }
    .footer { margin-top: 40px; padding-top: 16px; border-top: 2px solid #044889; font-size: 12px; color: #666; text-align: center; }
    @media print { body { padding: 20px; } }
  </style>
</head>
<body>
  <div style="text-align:center;margin-bottom:30px;">
    <h1 style="border:none;margin:0;">⚖️ المستشار القانوني الذكي</h1>
    <p style="color:#666;font-size:13px;">استشارة قانونية - نظام الأحوال الشخصية السعودي</p>
  </div>
  ${message.content.replace(/\n/g, '<br>').replace(/#{3}\s*(.+)/g, '<h3>$1</h3>').replace(/#{2}\s*(.+)/g, '<h2>$1</h2>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}
  <div class="footer">
    هذه استشارة قانونية أولية - لا تغني عن مراجعة محامٍ مرخص
  </div>
</body>
</html>`);
    w.document.close();
    w.print();
  };

  return (
    <div className={`animate-fade-in ${isUser ? 'flex justify-start' : ''}`}>
      <div
        className={`max-w-full rounded-2xl p-3 sm:p-4 ${
          isUser
            ? 'bg-primary-600 text-white max-w-[90%] sm:max-w-[80%]'
            : 'bg-white border border-gray-100 shadow-sm'
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : (
          <>
            {/* Copy & Print buttons - hidden during streaming */}
            {!message.isStreaming && <div className="flex items-center justify-end gap-2 mb-2 no-print">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-2.5 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
                title="نسخ"
              >
                {copied ? (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>تم النسخ</span>
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>نسخ</span>
                  </>
                )}
              </button>
              <button
                onClick={handlePrint}
                className="flex items-center gap-1 px-2.5 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
                title="طباعة"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                <span>طباعة</span>
              </button>
            </div>}

            <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed font-legal">
              <ReactMarkdown
                components={{
                  h2: ({ children }) => (
                    <h2 className="text-lg font-bold text-primary-800 mt-5 mb-2 border-b border-gray-100 pb-1 font-heading">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-bold text-primary-800 mt-4 mb-2 border-b border-gray-100 pb-1 font-heading">
                      {children}
                    </h3>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-gray-900">{children}</strong>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>
                  ),
                  p: ({ children }) => (
                    <p className="my-2 leading-loose">{children}</p>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-r-4 border-primary-300 pr-4 my-3 text-gray-700 bg-primary-50/30 py-2 rounded-l-lg">
                      {children}
                    </blockquote>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.isStreaming && (
                <span className="inline-block w-2 h-5 bg-primary-600 animate-pulse mr-1 align-text-bottom" />
              )}
            </div>
          </>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-xs font-medium text-gray-500 mb-2">المصادر:</p>
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {message.sources.map((src: any, i: number) => (
                <span
                  key={i}
                  className="inline-block px-2 py-1 bg-gray-50 text-gray-600 rounded text-xs"
                >
                  {src.chapter} - {src.topic}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Classification badge */}
        {message.classification && (
          <div className="mt-2 flex gap-2">
            <span className="inline-block px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full text-xs">
              {message.classification.category}
            </span>
            <span className="inline-block px-2 py-0.5 bg-gray-50 text-gray-600 rounded-full text-xs">
              {message.classification.intent}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
