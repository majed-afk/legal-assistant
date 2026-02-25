/**
 * Lightweight analytics helper — fire-and-forget event tracking.
 * Events are sent to the backend and stored in Supabase analytics_events table.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://legal-assistant-55zm.onrender.com/api';

export function trackEvent(eventType: string, eventData?: Record<string, any>) {
  // Fire-and-forget — don't await, don't block UI
  try {
    fetch(`${API_BASE}/analytics/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_type: eventType,
        event_data: eventData || {},
      }),
    }).catch(() => {
      // Silently ignore analytics failures
    });
  } catch {
    // Silently ignore
  }
}

// Pre-defined event types for type safety
export const EVENTS = {
  QUESTION_ASKED: 'question_asked',
  DRAFT_CREATED: 'draft_created',
  DEADLINE_CALCULATED: 'deadline_calculated',
  FEEDBACK_GIVEN: 'feedback_given',
  SEARCH_PERFORMED: 'search_performed',
  PAGE_VIEW: 'page_view',
} as const;
