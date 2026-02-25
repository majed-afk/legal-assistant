const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://legal-assistant-55zm.onrender.com/api';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

/** Common headers for all API requests (includes API key if configured). */
function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
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
  modelMode?: string
) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000); // 120s timeout

  try {
    const res = await fetch(`${API_BASE}/ask-stream`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ question, chat_history: chatHistory, model_mode: modelMode || '2.1' }),
      signal: controller.signal,
    });

    if (!res.ok) {
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
    const res = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers: getHeaders(),
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
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ query, topic, top_k: 10 }),
  });
  if (!res.ok) throw new Error('خطأ في البحث');
  return res.json();
}

export async function getArticles() {
  const res = await fetch(`${API_BASE}/articles`, { headers: getHeaders() });
  if (!res.ok) throw new Error('خطأ في تحميل المواد');
  return res.json();
}

export async function getTopics() {
  const res = await fetch(`${API_BASE}/articles/topics`, { headers: getHeaders() });
  if (!res.ok) throw new Error('خطأ');
  return res.json();
}

export async function draftDocument(draftType: string, caseDetails: any) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  try {
    const res = await fetch(`${API_BASE}/draft`, {
      method: 'POST',
      headers: getHeaders(),
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
  const res = await fetch(`${API_BASE}/draft/types`, { headers: getHeaders() });
  if (!res.ok) throw new Error('خطأ');
  return res.json();
}

export async function calculateDeadline(eventType: string, eventDate: string, details?: any) {
  const res = await fetch(`${API_BASE}/deadline`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ event_type: eventType, event_date: eventDate, details }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'خطأ' }));
    throw new Error(err.detail || 'حدث خطأ');
  }
  return res.json();
}

export async function getDeadlineTypes() {
  const res = await fetch(`${API_BASE}/deadline/types`, { headers: getHeaders() });
  if (!res.ok) throw new Error('خطأ');
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}
