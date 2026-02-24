'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/supabase/auth-context';
import { createClient } from '@/lib/supabase/client';
import {
  getConversations,
  deleteConversation,
  type Conversation,
} from '@/lib/supabase/conversations';

const toolItems = [
  { href: '/articles', label: 'استعراض النظام', icon: '📖' },
  { href: '/draft', label: 'صياغة المذكرات', icon: '📝' },
  { href: '/deadlines', label: 'حاسبة المهل', icon: '⏰' },
];

function groupConversations(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const lastWeek = new Date(today.getTime() - 7 * 86400000);
  const lastMonth = new Date(today.getTime() - 30 * 86400000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'اليوم', items: [] },
    { label: 'أمس', items: [] },
    { label: 'آخر 7 أيام', items: [] },
    { label: 'آخر 30 يوم', items: [] },
    { label: 'أقدم', items: [] },
  ];

  for (const conv of conversations) {
    const d = new Date(conv.updated_at);
    if (d >= today) groups[0].items.push(conv);
    else if (d >= yesterday) groups[1].items.push(conv);
    else if (d >= lastWeek) groups[2].items.push(conv);
    else if (d >= lastMonth) groups[3].items.push(conv);
    else groups[4].items.push(conv);
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const supabase = createClient();

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations(supabase);
      setConversations(data);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 5000);
    return () => clearInterval(interval);
  }, [loadConversations]);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Close sidebar on escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await deleteConversation(supabase, id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (pathname === `/chat/${id}`) {
        router.push('/chat');
      }
    } catch {
      // silently fail
    }
  };

  const grouped = groupConversations(conversations);

  return (
    <>
      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 right-0 left-0 z-40 bg-white/80 backdrop-blur-lg border-b border-gray-200/60 flex items-center justify-between px-4 py-3">
        <button
          onClick={() => setOpen(!open)}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          aria-label="القائمة"
        >
          <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {open ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
            </svg>
          </div>
          <span className="text-sm font-bold text-gray-800">Sanad AI</span>
        </div>
        <div className="w-9" />
      </div>

      {/* Overlay (mobile only) */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 bg-black/30 z-40 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed right-0 top-0 h-full w-72 bg-gray-50 border-l border-gray-200 flex flex-col z-50 transition-transform duration-300 ease-in-out ${
          open ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Header */}
        <div className="p-4 pb-3">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center shadow-sm">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
                </svg>
              </div>
              <span className="text-base font-bold text-gray-800">Sanad AI</span>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="lg:hidden p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
              aria-label="إغلاق"
            >
              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* New Chat button */}
          <Link
            href="/chat"
            className="flex items-center gap-2 w-full px-3.5 py-2.5 rounded-xl border border-gray-300 text-sm font-medium text-gray-700 hover:bg-white hover:shadow-sm transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            محادثة جديدة
          </Link>
        </div>

        {/* Conversations list */}
        <div className="flex-1 overflow-y-auto px-3 pb-2">
          {grouped.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-xs">
              لا توجد محادثات سابقة
            </div>
          ) : (
            grouped.map((group) => (
              <div key={group.label} className="mb-3">
                <p className="text-[11px] font-medium text-gray-400 px-2 py-1.5 uppercase tracking-wide">
                  {group.label}
                </p>
                {group.items.map((conv) => {
                  const isActive = pathname === `/chat/${conv.id}`;
                  return (
                    <Link
                      key={conv.id}
                      href={`/chat/${conv.id}`}
                      onMouseEnter={() => setHoveredId(conv.id)}
                      onMouseLeave={() => setHoveredId(null)}
                      className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm transition-colors mb-0.5 relative ${
                        isActive
                          ? 'bg-white shadow-sm text-gray-900 font-medium'
                          : 'text-gray-600 hover:bg-white/60 hover:text-gray-800'
                      }`}
                    >
                      <span className="truncate flex-1">{conv.title}</span>
                      {(hoveredId === conv.id || isActive) && (
                        <button
                          onClick={(e) => handleDelete(conv.id, e)}
                          className="flex-shrink-0 p-1 rounded hover:bg-red-50 hover:text-red-500 text-gray-400 transition-colors"
                          title="حذف المحادثة"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </Link>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200" />

        {/* Tools section */}
        <div className="px-3 py-2">
          <p className="text-[11px] font-medium text-gray-400 px-2 py-1 uppercase tracking-wide">أدوات</p>
          {toolItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors mb-0.5 ${
                  isActive
                    ? 'bg-white shadow-sm text-gray-900 font-medium'
                    : 'text-gray-600 hover:bg-white/60 hover:text-gray-800'
                }`}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200" />

        {/* User section */}
        <div className="p-3">
          <div className="flex items-center gap-3 px-2.5 py-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {user?.email?.charAt(0).toUpperCase() || '?'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-800 truncate">{user?.email || ''}</p>
            </div>
            <button
              onClick={signOut}
              className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="تسجيل الخروج"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
