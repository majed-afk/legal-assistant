import { createClient } from './supabase/client';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://legal-assistant-55zm.onrender.com/api';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

/** Common headers for all API requests. Uses JWT from Supabase session (primary) or API key (fallback). */
async function getHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };

  // JWT from Supabase Auth (primary)
  try {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
      return headers;
    }
  } catch {
    // Supabase not available — fall through to API key
  }

  // API key fallback (legacy)
  if (API_KEY) headers['X-API-Key'] = API_KEY;
  return headers;
}

// --- Streaming API ---

interface StreamCallbacks {
  onMeta: (data: { classification: any; sources: any[]; has_deadlines: boolean }) => void;
  onToken: (text: string) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

export async function askQuestionStreaming(
  question: string,
  callbacks: StreamCallbacks,
  chatHistory?: any[],
  modelMode?: string,
  abortController?: AbortController
) {
  const controller = abortController || new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000); // 120s timeout

  try {
    const headers = await getHeaders();
    const res = await fetch(`${API_BASE}/ask-stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ question, chat_history: chatHistory, model_mode: modelMode || '2.1' }),
      signal: controller.signal,
    });

    if (!res.ok) {
      if (res.status === 401) throw new Error('انتهت الجلسة — سجّل دخولك مرة أخرى');
      if (res.status === 429) throw new Error('تجاوزت الحد المسموح — يرجى الترقية أو الانتظار');
      if (res.status === 503) throw new Error('الخادم في صيانة — جرب مرة أخرى بعد قليل');
      const err = await res.json().catch(() => ({ detail: 'خطأ في الاتصال' }));
      throw new Error(err.detail || 'حدث خطأ');
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error('Streaming غير مدعوم');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events from buffer
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;

        try {
          const event = JSON.parse(jsonStr);

          switch (event.type) {
            case 'meta':
              callbacks.onMeta({
                classification: event.classification,
                sources: event.sources,
                has_deadlines: event.has_deadlines,
              });
              break;
            case 'token':
              callbacks.onToken(event.text);
              break;
            case 'done':
              callbacks.onDone();
              break;
            case 'error':
              callbacks.onError(event.message);
              break;
          }
        } catch {
          // Skip malformed JSON
        }
      }
    }
  } catch (e: any) {
    if (e.name === 'AbortError') {
      callbacks.onError('انتهت المهلة — جرب مرة أخرى');
    } else if (typeof navigator !== 'undefined' && !navigator.onLine) {
      callbacks.onError('لا يوجد اتصال بالإنترنت — تحقق من شبكتك');
    } else {
      callbacks.onError(e.message || 'حدث خطأ في الاتصال');
    }
  } finally {
    clearTimeout(timeout);
  }

  return controller;
}

// --- Legacy non-streaming API (kept for backward compatibility) ---

export async function askQuestion(question: string, chatHistory?: any[]) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  try {
    const headers = await getHeaders();
    const res = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ question, chat_history: chatHistory }),
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'خطأ في الاتصال' }));
      throw new Error(err.detail || 'حدث خطأ');
    }
    return res.json();
  } catch (e: any) {
    if (e.name === 'AbortError') {
      throw new Error('انتهت المهلة — جرب مرة أخرى');
    }
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}

export async function searchArticles(query: string, topic?: string) {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, topic, top_k: 10 }),
  });
  if (!res.ok) throw new Error('خطأ في البحث');
  return res.json();
}

export async function getArticles() {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/articles`, { headers });
  if (!res.ok) throw new Error('خطأ في تحميل المواد');
  return res.json();
}

export async function getTopics() {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/articles/topics`, { headers });
  if (!res.ok) throw new Error('خطأ');
  return res.json();
}

export async function draftDocument(draftType: string, caseDetails: any) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  try {
    const headers = await getHeaders();
    const res = await fetch(`${API_BASE}/draft`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ draft_type: draftType, case_details: caseDetails }),
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'خطأ في صياغة المذكرة' }));
      throw new Error(err.detail || 'حدث خطأ');
    }
    return res.json();
  } catch (e: any) {
    if (e.name === 'AbortError') {
      throw new Error('انتهت المهلة — جرب مرة أخرى');
    }
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getDraftTypes() {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/draft/types`, { headers });
  if (!res.ok) throw new Error('خطأ');
  return res.json();
}

export async function calculateDeadline(eventType: string, eventDate: string, details?: any) {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/deadline`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ event_type: eventType, event_date: eventDate, details }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'خطأ' }));
    throw new Error(err.detail || 'حدث خطأ');
  }
  return res.json();
}

export async function getDeadlineTypes() {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/deadline/types`, { headers });
  if (!res.ok) throw new Error('خطأ');
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}


// --- Subscription & Payment APIs ---

export async function getPlans() {
  const res = await fetch(`${API_BASE}/plans`);
  if (!res.ok) throw new Error('خطأ في تحميل الباقات');
  return res.json();
}

export async function getSubscription() {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/subscription`, { headers });
  if (!res.ok) throw new Error('خطأ في تحميل الاشتراك');
  return res.json();
}

export async function createSubscription(planTier: string, billingCycle: string = 'monthly') {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/subscription/create`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ plan_tier: planTier, billing_cycle: billingCycle }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'خطأ في إنشاء الاشتراك' }));
    throw new Error(err.detail || 'حدث خطأ');
  }
  return res.json();
}

export async function verifyPayment(paymentId: string, txId?: string) {
  const headers = await getHeaders();
  const params = new URLSearchParams({ payment_id: paymentId });
  if (txId) params.append('tx_id', txId);
  const res = await fetch(`${API_BASE}/subscription/verify?${params}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'خطأ في التحقق من الدفع' }));
    throw new Error(err.detail || 'حدث خطأ');
  }
  return res.json();
}

export async function cancelSubscription() {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/subscription/cancel`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'خطأ في إلغاء الاشتراك' }));
    throw new Error(err.detail || 'حدث خطأ');
  }
  return res.json();
}

export async function getUsage() {
  const headers = await getHeaders();
  const res = await fetch(`${API_BASE}/usage`, { headers });
  if (!res.ok) throw new Error('خطأ في تحميل الاستخدام');
  return res.json();
}
