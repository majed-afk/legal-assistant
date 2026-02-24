'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { askQuestionStreaming } from '@/lib/api';
import { createClient } from '@/lib/supabase/client';
import {
  createConversation,
  getMessages,
  addMessage,
  updateConversationTitle,
} from '@/lib/supabase/conversations';
import MessageBubble from './MessageBubble';
import ModelSelector from './ModelSelector';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  classification?: any;
  isStreaming?: boolean;
}

interface Props {
  conversationId?: string;
}

const QUICK_QUESTIONS = [
  'ما هي شروط عقد الزواج؟',
  'كيف يتم الخلع في النظام السعودي؟',
  'ما هي حقوق الحضانة بعد الطلاق؟',
  'كم مدة عدة المطلقة؟',
  'ما هي أحكام النفقة على الزوج؟',
  'كيف يتم توزيع الميراث؟',
];

export default function ChatInterface({ conversationId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [modelMode, setModelMode] = useState('2.1');
  const [currentConvId, setCurrentConvId] = useState<string | null>(conversationId || null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const streamingContentRef = useRef('');
  const streamingMetaRef = useRef<{ sources?: any[]; classification?: any }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const supabase = createClient();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  // Load existing conversation messages
  useEffect(() => {
    if (conversationId) {
      setCurrentConvId(conversationId);
      setLoadingHistory(true);
      getMessages(supabase, conversationId)
        .then((msgs) => {
          setMessages(
            msgs.map((m) => ({
              role: m.role,
              content: m.content,
              sources: m.sources,
              classification: m.classification,
            }))
          );
        })
        .catch(() => {})
        .finally(() => setLoadingHistory(false));
    } else {
      setMessages([]);
      setCurrentConvId(null);
    }
  }, [conversationId]);

  const sendMessage = useCallback(async (question?: string) => {
    const q = question || input.trim();
    if (!q || loading) return;

    setInput('');
    const userMsg: Message = { role: 'user', content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    streamingContentRef.current = '';
    streamingMetaRef.current = {};

    // Create conversation if it doesn't exist
    let convId = currentConvId;
    if (!convId) {
      try {
        const conv = await createConversation(supabase, q.slice(0, 60), modelMode);
        convId = conv.id;
        setCurrentConvId(convId);
        // Navigate to the conversation URL without full page reload
        router.replace(`/chat/${convId}`, { scroll: false });
      } catch (err) {
        console.error('Failed to create conversation:', err);
      }
    }

    // Save user message to Supabase
    if (convId) {
      addMessage(supabase, convId, 'user', q).catch(() => {});
      // Update title on first message
      if (messages.length === 0) {
        updateConversationTitle(supabase, convId, q.slice(0, 60)).catch(() => {});
      }
    }

    // Add empty streaming message
    const streamingMsg: Message = {
      role: 'assistant',
      content: '',
      isStreaming: true,
    };
    setMessages((prev) => [...prev, streamingMsg]);

    // Build chat history for API
    const recentMessages = messages.slice(-4);
    const chatHistory = recentMessages.map((m) => ({
      role: m.role,
      content: m.role === 'assistant'
        ? m.content.slice(0, 500) + (m.content.length > 500 ? '...' : '')
        : m.content,
    }));

    const savedConvId = convId; // capture for closure

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

          // Save assistant message to Supabase
          if (savedConvId) {
            addMessage(supabase, savedConvId, 'assistant', streamingContentRef.current, {
              sources: streamingMetaRef.current.sources,
              classification: streamingMetaRef.current.classification,
              model_mode: modelMode,
            }).catch(() => {});
          }
        },
        onError: (error) => {
          if (streamingContentRef.current) {
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: streamingContentRef.current + `\n\n${error}`,
                isStreaming: false,
              };
              return updated;
            });
          } else {
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              updated[lastIdx] = {
                role: 'assistant',
                content: `${error}`,
                isStreaming: false,
              };
              return updated;
            });
          }
          setLoading(false);
        },
      },
      chatHistory.length > 0 ? chatHistory : undefined,
      modelMode
    );
  }, [input, loading, messages, modelMode, currentConvId, router]);

  if (loadingHistory) {
    return (
      <div className="flex flex-col h-[calc(100vh-3.5rem)] lg:h-screen items-center justify-center">
        <div className="flex items-center gap-3 text-gray-400">
          <div className="loading-dot" />
          <div className="loading-dot" />
          <div className="loading-dot" />
          <span className="text-sm mr-2">جاري تحميل المحادثة...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] lg:h-screen">
      {/* Top bar with model selector */}
      <div className="border-b border-gray-100 bg-white/60 backdrop-blur-sm px-4 py-2 flex items-center justify-between">
        <ModelSelector value={modelMode} onChange={setModelMode} disabled={loading} />
        <div className="text-xs text-gray-400">
          {messages.length > 0 && `${messages.filter(m => m.role === 'user').length} رسالة`}
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto mt-8 lg:mt-16 text-center px-2">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-600 to-primary-800 shadow-lg shadow-primary-500/20 mb-4">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
              </svg>
            </div>
            <h2 className="text-xl lg:text-2xl font-bold text-gray-800 mb-2 font-heading">مرحباً بك في سند</h2>
            <p className="text-sm lg:text-base text-gray-500 mb-6 lg:mb-8">
              اسأل أي سؤال عن الأحوال الشخصية أو الإثبات أو المرافعات الشرعية
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
              {QUICK_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  className="text-right p-3.5 rounded-xl border border-gray-200 text-sm text-gray-700 hover:bg-primary-50 hover:border-primary-200 hover:text-primary-700 active:bg-primary-100 transition-all hover:shadow-sm"
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
                <span className="text-sm text-gray-400 mr-2">جاري التفكير...</span>
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
              className="flex-1 px-3 sm:px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-gray-50 focus:bg-white transition-colors"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 sm:px-6 py-3 bg-gradient-to-l from-primary-600 to-primary-700 text-white rounded-xl text-sm font-medium hover:from-primary-700 hover:to-primary-800 active:from-primary-800 active:to-primary-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md whitespace-nowrap"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
          <p className="text-center text-[10px] text-gray-400 mt-2">
            سند يقدم استشارات أولية — يُنصح بمراجعة محامٍ مرخص للقرارات المهمة
          </p>
        </div>
      </div>
    </div>
  );
}
