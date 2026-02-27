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
import UsageLimitBanner from './UsageLimitBanner';
import { motion, AnimatePresence } from 'framer-motion';
import { trackEvent, EVENTS } from '@/lib/analytics';
import { useSubscription } from '@/lib/supabase/subscription-context';

interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  classification?: any;
  isStreaming?: boolean;
  isError?: boolean;
}

interface Props {
  conversationId?: string;
}

const QUICK_QUESTIONS = [
  { q: 'ما هي شروط عقد الزواج؟', icon: '💍' },
  { q: 'ما هي حقوق الحضانة بعد الطلاق؟', icon: '👨‍👧' },
  { q: 'ما هي ضمانات العيب في البيع؟', icon: '🏷️' },
  { q: 'ما هي التزامات المؤجر والمستأجر؟', icon: '🏠' },
  { q: 'كيف يتم توزيع الميراث؟', icon: '📜' },
  { q: 'ما هي طرق الإثبات أمام المحكمة؟', icon: '⚖️' },
];

export default function ChatInterface({ conversationId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [modelMode, setModelMode] = useState('2.1');
  const [currentConvId, setCurrentConvId] = useState<string | null>(conversationId || null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const streamingContentRef = useRef('');
  const streamingMetaRef = useRef<{ sources?: any[]; classification?: any }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const pendingRetryRef = useRef<{ question: string; skipUserMessage: boolean } | null>(null);
  const router = useRouter();
  const supabase = createClient();
  const { canPerformAction, refreshUsage } = useSubscription();

  // Smart scroll — only auto-scroll if user hasn't scrolled up
  const scrollToBottom = useCallback(() => {
    if (!userScrolledUp) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [userScrolledUp]);

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    setUserScrolledUp(!isNearBottom);
  }, []);

  const scrollToBottomForced = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setUserScrolledUp(false);
  }, []);

  // Auto-resize textarea
  const adjustTextarea = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    }
  };

  // Load existing conversation messages
  useEffect(() => {
    if (conversationId) {
      setCurrentConvId(conversationId);
      setLoadingHistory(true);
      getMessages(supabase, conversationId)
        .then((msgs) => {
          setMessages(
            msgs.map((m) => ({
              id: m.id,
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

  // Notify sidebar of conversation changes
  const notifySidebar = useCallback(() => {
    window.dispatchEvent(new CustomEvent('conversations-changed'));
  }, []);

  const stopGenerating = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
    setIsThinking(false);
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated.length - 1;
      if (last >= 0 && updated[last]?.isStreaming) {
        updated[last] = {
          ...updated[last],
          content: streamingContentRef.current || updated[last].content,
          isStreaming: false,
        };
      }
      return updated;
    });
  }, []);

  const sendMessage = useCallback(async (question?: string, options?: { skipUserMessage?: boolean }) => {
    const q = question || input.trim();
    if (!q || loading) return;

    if (!options?.skipUserMessage) {
      setInput('');
      if (textareaRef.current) { textareaRef.current.style.height = 'auto'; }
      const userMsg: Message = { role: 'user', content: q };
      setMessages((prev) => [...prev, userMsg]);
    }

    setLoading(true);
    setIsThinking(true);
    setUserScrolledUp(false);
    streamingContentRef.current = '';
    streamingMetaRef.current = {};

    // Create conversation if doesn't exist
    let convId = currentConvId;
    if (!convId) {
      try {
        const conv = await createConversation(supabase, q.slice(0, 60), modelMode);
        convId = conv.id;
        setCurrentConvId(convId);
        router.replace(`/chat/${convId}`, { scroll: false });
        notifySidebar();
      } catch (err) {
        console.error('Failed to create conversation:', err);
      }
    }

    // Save user message (skip if regenerating)
    if (convId && !options?.skipUserMessage) {
      addMessage(supabase, convId, 'user', q).catch(() => {});
      if (messages.length === 0) {
        updateConversationTitle(supabase, convId, q.slice(0, 60)).catch(() => {});
      }
    }

    // Add empty streaming message
    setMessages((prev) => [...prev, { role: 'assistant', content: '', isStreaming: true }]);

    // Build chat history
    const recentMessages = messages.slice(-4);
    const chatHistory = recentMessages
      .filter((m, i) => !(options?.skipUserMessage && i === recentMessages.length - 1 && m.role === 'user'))
      .map((m) => ({
        role: m.role,
        content: m.role === 'assistant' ? m.content.slice(0, 500) + (m.content.length > 500 ? '...' : '') : m.content,
      }));

    // Track analytics event
    trackEvent(EVENTS.QUESTION_ASKED, {
      question_length: q.length,
      model_mode: modelMode,
      conversation_id: convId,
      has_history: chatHistory.length > 0,
    });

    const savedConvId = convId;

    // Create AbortController and pass it to the API
    const controller = new AbortController();
    abortRef.current = controller;

    await askQuestionStreaming(
      q,
      {
        onMeta: (data) => {
          streamingMetaRef.current = { sources: data.sources, classification: data.classification };
        },
        onToken: (text) => {
          setIsThinking(false);
          streamingContentRef.current += text;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated.length - 1;
            updated[last] = { ...updated[last], content: streamingContentRef.current, isStreaming: true };
            return updated;
          });
        },
        onDone: () => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated.length - 1;
            updated[last] = {
              ...updated[last],
              content: streamingContentRef.current,
              sources: streamingMetaRef.current.sources,
              classification: streamingMetaRef.current.classification,
              isStreaming: false,
            };
            return updated;
          });
          setLoading(false);
          setIsThinking(false);
          abortRef.current = null;

          if (savedConvId) {
            addMessage(supabase, savedConvId, 'assistant', streamingContentRef.current, {
              sources: streamingMetaRef.current.sources,
              classification: streamingMetaRef.current.classification,
              model_mode: modelMode,
            }).then((savedMsg) => {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated.length - 1;
                updated[last] = { ...updated[last], id: savedMsg.id };
                return updated;
              });
              notifySidebar();
            }).catch(() => {});
          }
        },
        onError: (error) => {
          const hasPartialContent = !!streamingContentRef.current;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated.length - 1;
            updated[last] = {
              role: 'assistant',
              content: hasPartialContent ? streamingContentRef.current + `\n\n${error}` : error,
              isStreaming: false,
              isError: !hasPartialContent,
            };
            return updated;
          });
          setLoading(false);
          setIsThinking(false);
          abortRef.current = null;
        },
      },
      chatHistory.length > 0 ? chatHistory : undefined,
      modelMode,
      controller
    );
  }, [input, loading, messages, modelMode, currentConvId, router, notifySidebar]);

  const retryLastMessage = useCallback(() => {
    if (loading) return;
    let lastUserQ = '';
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        lastUserQ = messages[i].content;
        break;
      }
    }
    if (!lastUserQ) return;

    setMessages((prev) => {
      const newMsgs = [...prev];
      if (newMsgs.length > 0 && newMsgs[newMsgs.length - 1].role === 'assistant') newMsgs.pop();
      if (newMsgs.length > 0 && newMsgs[newMsgs.length - 1].role === 'user') newMsgs.pop();
      return newMsgs;
    });

    pendingRetryRef.current = { question: lastUserQ, skipUserMessage: false };
  }, [messages, loading]);

  const regenerateResponse = useCallback(() => {
    if (loading) return;
    let lastUserQ = '';
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        lastUserQ = messages[i].content;
        break;
      }
    }
    if (!lastUserQ) return;

    setMessages((prev) => {
      const newMsgs = [...prev];
      if (newMsgs.length > 0 && newMsgs[newMsgs.length - 1].role === 'assistant') newMsgs.pop();
      return newMsgs;
    });

    pendingRetryRef.current = { question: lastUserQ, skipUserMessage: true };
  }, [messages, loading]);

  // Pending retry handler — re-sends after messages state update
  useEffect(() => {
    if (pendingRetryRef.current && !loading) {
      const { question, skipUserMessage } = pendingRetryRef.current;
      pendingRetryRef.current = null;
      sendMessage(question, { skipUserMessage });
    }
  }, [messages, loading, sendMessage]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && loading) {
        stopGenerating();
      }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        router.push('/chat');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [loading, router, stopGenerating]);

  if (loadingHistory) {
    return (
      <div className="flex flex-col h-[calc(100vh-3.5rem)] lg:h-screen items-center justify-center bg-surface-50">
        <div className="w-full max-w-3xl px-4 space-y-4">
          {/* User message skeleton */}
          <div className="flex justify-start">
            <div className="w-[60%] h-12 rounded-2xl bg-gradient-to-l from-primary-500/15 to-primary-600/5 animate-pulse" />
          </div>
          {/* Assistant message skeleton */}
          <div className="w-full space-y-2">
            <div className="h-4 w-3/4 rounded-lg bg-gray-200/60 animate-pulse" />
            <div className="h-4 w-full rounded-lg bg-gray-200/40 animate-pulse" />
            <div className="h-4 w-5/6 rounded-lg bg-gray-200/50 animate-pulse" />
            <div className="h-4 w-2/3 rounded-lg bg-gray-200/30 animate-pulse" />
          </div>
          {/* Second pair */}
          <div className="flex justify-start mt-6">
            <div className="w-[45%] h-10 rounded-2xl bg-gradient-to-l from-primary-500/15 to-primary-600/5 animate-pulse" />
          </div>
          <div className="w-full space-y-2">
            <div className="h-4 w-2/3 rounded-lg bg-gray-200/60 animate-pulse" />
            <div className="h-4 w-full rounded-lg bg-gray-200/40 animate-pulse" />
            <div className="h-4 w-4/5 rounded-lg bg-gray-200/50 animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] lg:h-screen bg-surface-50">
      {/* Top bar */}
      <div className="border-b border-gray-100/50 bg-white/70 backdrop-blur-xl px-4 py-2 flex items-center justify-between">
        <ModelSelector value={modelMode} onChange={setModelMode} disabled={loading} />
        <div className="text-xs text-gray-400">
          {messages.length > 0 && `${messages.filter(m => m.role === 'user').length} رسالة`}
        </div>
      </div>

      {/* Messages area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6 relative"
      >
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto mt-8 lg:mt-16 text-center px-2">
            {/* Animated logo */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-glow mb-5 animate-float ring-2 ring-gold-400/15"
            >
              <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
              </svg>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-2xl lg:text-3xl font-bold gradient-text mb-2 font-heading"
            >
              مرحباً بك في سند
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.15 }}
              className="text-sm lg:text-base text-gray-500 mb-8"
            >
              اسأل أي سؤال عن الأحوال الشخصية أو المعاملات المدنية أو الإثبات أو المرافعات
            </motion.p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3">
              {QUICK_QUESTIONS.map((item, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.2 + i * 0.05 }}
                  onClick={() => sendMessage(item.q)}
                  className="text-right p-4 rounded-2xl bg-white/60 backdrop-blur-sm border border-gray-200/50 text-sm text-gray-700 hover:bg-white hover:shadow-elevated hover:border-primary-200/50 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-300 flex items-start gap-3"
                >
                  <span className="text-lg mt-0.5 opacity-60">{item.icon}</span>
                  <span>{item.q}</span>
                </motion.button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-4 sm:space-y-5">
            {messages.map((msg, i) => (
              <MessageBubble
                key={msg.id || i}
                message={msg}
                conversationId={currentConvId || undefined}
                isLastAssistant={i === messages.length - 1 && msg.role === 'assistant' && !msg.isStreaming && !loading}
                onRetry={msg.isError ? retryLastMessage : undefined}
                onRegenerate={
                  i === messages.length - 1 &&
                  msg.role === 'assistant' &&
                  !msg.isStreaming &&
                  !loading &&
                  !msg.isError
                    ? regenerateResponse
                    : undefined
                }
              />
            ))}

            {/* Thinking indicator — shows before first token arrives */}
            <AnimatePresence>
              {isThinking && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-3 p-4"
                >
                  <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-2xl bg-white/80 backdrop-blur-sm border border-gray-100/80 shadow-sm">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-primary-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-primary-600 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm text-gray-500 mr-1">سند يفكر...</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Scroll to bottom FAB */}
        <AnimatePresence>
          {userScrolledUp && messages.length > 0 && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={scrollToBottomForced}
              className="sticky bottom-4 mx-auto flex w-10 h-10 rounded-full bg-white/90 backdrop-blur-sm border border-gray-200/50 shadow-elevated items-center justify-center text-gray-500 hover:text-primary-600 hover:shadow-glow transition-all duration-300"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* Usage limit banner */}
      <UsageLimitBanner action="questions" />

      {/* Stop generating button */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="flex justify-center pb-2"
          >
            <button
              onClick={stopGenerating}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/80 backdrop-blur-sm border border-gray-200/50 text-sm text-gray-600 hover:bg-white hover:shadow-elevated hover:border-gray-300/50 transition-all duration-300"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
              إيقاف التوليد
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating input */}
      <div className="p-3 sm:p-4 pb-4 sm:pb-6 bg-gradient-to-t from-surface-50 via-surface-50 to-transparent">
        <div className="max-w-3xl mx-auto">
          <form
            onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
            className="input-glass flex items-end gap-2 p-2 transition-all duration-300 focus-within:border-primary-300/50 focus-within:shadow-[0_0_15px_rgba(99,102,241,0.1)]"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => { setInput(e.target.value); adjustTextarea(); }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
              }}
              placeholder={loading ? 'سند يعمل على إجابتك...' : 'اكتب سؤالك القانوني هنا...'}
              className="flex-1 px-3 py-2.5 bg-transparent border-0 text-sm focus:outline-none focus:ring-0 resize-none min-h-[40px] max-h-[120px]"
              rows={1}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 text-white flex items-center justify-center hover:shadow-glow disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-300 flex-shrink-0"
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
