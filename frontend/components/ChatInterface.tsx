'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { askQuestionStreaming } from '@/lib/api';
import MessageBubble from './MessageBubble';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  classification?: any;
  isStreaming?: boolean;
}

const QUICK_QUESTIONS = [
  'ما هي شروط عقد الزواج؟',
  'كيف يتم الخلع في النظام السعودي؟',
  'ما هي حقوق الحضانة بعد الطلاق؟',
  'كم مدة عدة المطلقة؟',
  'ما هي أحكام النفقة على الزوج؟',
  'كيف يتم توزيع الميراث؟',
];

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const streamingContentRef = useRef('');
  const streamingMetaRef = useRef<{ sources?: any[]; classification?: any }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = useCallback(async (question?: string) => {
    const q = question || input.trim();
    if (!q || loading) return;

    setInput('');
    const userMsg: Message = { role: 'user', content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    streamingContentRef.current = '';
    streamingMetaRef.current = {};

    // Add empty streaming message
    const streamingMsg: Message = {
      role: 'assistant',
      content: '',
      isStreaming: true,
    };
    setMessages((prev) => [...prev, streamingMsg]);

    // Limit chat history to last 4 messages and trim assistant responses
    // to reduce token count and avoid rate limits
    const recentMessages = messages.slice(-4);
    const chatHistory = recentMessages.map((m) => ({
      role: m.role,
      content: m.role === 'assistant'
        ? m.content.slice(0, 500) + (m.content.length > 500 ? '...' : '')
        : m.content,
    }));

    await askQuestionStreaming(
      q,
      {
        onMeta: (data) => {
          streamingMetaRef.current = {
            sources: data.sources,
            classification: data.classification,
          };
        },
        onToken: (text) => {
          streamingContentRef.current += text;
          // Update the last message (streaming message)
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: streamingContentRef.current,
              isStreaming: true,
            };
            return updated;
          });
        },
        onDone: () => {
          // Finalize the streaming message
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: streamingContentRef.current,
              sources: streamingMetaRef.current.sources,
              classification: streamingMetaRef.current.classification,
              isStreaming: false,
            };
            return updated;
          });
          setLoading(false);
        },
        onError: (error) => {
          if (streamingContentRef.current) {
            // If we got partial content, keep it and add error
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: streamingContentRef.current + `\n\n⚠️ ${error}`,
                isStreaming: false,
              };
              return updated;
            });
          } else {
            // No content received, show error message
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              updated[lastIdx] = {
                role: 'assistant',
                content: `⚠️ ${error}`,
                isStreaming: false,
              };
              return updated;
            });
          }
          setLoading(false);
        },
      },
      chatHistory.length > 0 ? chatHistory : undefined
    );
  }, [input, loading, messages]);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] lg:h-screen">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto mt-8 lg:mt-16 text-center px-2">
            <div className="text-5xl lg:text-6xl mb-3 lg:mb-4">⚖️</div>
            <h2 className="text-xl lg:text-2xl font-bold text-gray-800 mb-2">مساعد الأحوال الشخصية</h2>
            <p className="text-sm lg:text-base text-gray-500 mb-6 lg:mb-8">
              اسأل أي سؤال عن نظام الأحوال الشخصية السعودي
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
              {QUICK_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  className="text-right p-3 rounded-xl border border-gray-200 text-sm text-gray-700 hover:bg-primary-50 hover:border-primary-200 hover:text-primary-700 active:bg-primary-100 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-3 sm:space-y-4">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            {loading && messages[messages.length - 1]?.content === '' && (
              <div className="flex items-center gap-2 p-3 sm:p-4 animate-fade-in">
                <div className="loading-dot" />
                <div className="loading-dot" />
                <div className="loading-dot" />
                <span className="text-sm text-gray-400 mr-2">جاري الاتصال...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white p-3 sm:p-4">
        <div className="max-w-3xl mx-auto">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex gap-2 sm:gap-3"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="اكتب سؤالك القانوني هنا..."
              className="flex-1 px-3 sm:px-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 sm:px-6 py-3 bg-primary-600 text-white rounded-xl text-sm font-medium hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              إرسال
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
