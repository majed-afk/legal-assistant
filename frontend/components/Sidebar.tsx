'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/supabase/auth-context';
import { createClient } from '@/lib/supabase/client';
import { getConversations, deleteConversation, updateConversationTitle } from '@/lib/supabase/conversations';
import { useTheme } from '@/lib/theme-context';
import SubscriptionBadge from '@/components/SubscriptionBadge';
import UsageBar from '@/components/UsageBar';
import clsx from 'clsx';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

function groupByDate(convs: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const week = new Date(today.getTime() - 7 * 86400000);
  const month = new Date(today.getTime() - 30 * 86400000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'اليوم', items: [] },
    { label: 'أمس', items: [] },
    { label: 'آخر 7 أيام', items: [] },
    { label: 'آخر 30 يوم', items: [] },
    { label: 'أقدم', items: [] },
  ];

  convs.forEach((c) => {
    const d = new Date(c.updated_at || c.created_at);
    if (d >= today) groups[0].items.push(c);
    else if (d >= yesterday) groups[1].items.push(c);
    else if (d >= week) groups[2].items.push(c);
    else if (d >= month) groups[3].items.push(c);
    else groups[4].items.push(c);
  });

  return groups.filter((g) => g.items.length > 0);
}

export default function Sidebar() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const editInputRef = useRef<HTMLInputElement>(null);
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const supabase = createClient();

  const loadConversations = useCallback(async () => {
    if (!user) return;
    try {
      const data = await getConversations(supabase);
      setConversations(data);
    } catch {}
  }, [user]);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  useEffect(() => {
    const handleConvChanged = () => loadConversations();
    window.addEventListener('conversations-changed', handleConvChanged);
    const iv = setInterval(loadConversations, 60000);
    return () => {
      window.removeEventListener('conversations-changed', handleConvChanged);
      clearInterval(iv);
    };
  }, [loadConversations]);

  useEffect(() => { setMobileOpen(false); }, [pathname]);
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setMobileOpen(false); setDeleteConfirm(null); }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, []);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const handleDeleteRequest = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleteConfirm(id);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteConversation(supabase, deleteConfirm);
      setConversations((p) => p.filter((c) => c.id !== deleteConfirm));
      if (pathname === `/chat/${deleteConfirm}`) router.push('/chat');
    } catch {}
    setDeleteConfirm(null);
  };

  const startEditing = (conv: Conversation, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title || '');
  };

  const saveTitle = async () => {
    if (!editingId || !editTitle.trim()) { setEditingId(null); return; }
    try {
      await updateConversationTitle(supabase, editingId, editTitle.trim());
      setConversations((prev) =>
        prev.map((c) => c.id === editingId ? { ...c, title: editTitle.trim() } : c)
      );
    } catch {}
    setEditingId(null);
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); saveTitle(); }
    if (e.key === 'Escape') { setEditingId(null); }
  };

  const currentConvId = pathname.startsWith('/chat/') ? pathname.split('/chat/')[1] : null;

  const filteredConversations = searchQuery.trim()
    ? conversations.filter((c) => (c.title || '').toLowerCase().includes(searchQuery.toLowerCase()))
    : conversations;

  const groups = groupByDate(filteredConversations);

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="p-4 pb-3">
        <Link href="/chat" className="flex items-center gap-2.5 group mb-4" aria-label="الصفحة الرئيسية">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm group-hover:shadow-glow transition-shadow duration-300">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
            </svg>
          </div>
          <span className="text-white font-bold text-lg font-heading">Sanad AI</span>
        </Link>

        <Link href="/chat" className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-primary-500/10 border border-primary-500/20 text-primary-300 text-sm font-medium hover:bg-primary-500/20 hover:border-primary-500/30 transition-all duration-300" aria-label="محادثة جديدة">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          محادثة جديدة
        </Link>

        {conversations.length > 3 && (
          <div className="mt-3 relative">
            <svg className="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="بحث في المحادثات..." aria-label="بحث في المحادثات" className="w-full py-2 pr-8 pl-3 bg-white/5 border border-white/10 rounded-lg text-xs text-gray-300 placeholder-gray-500 focus:outline-none focus:border-primary-500/30 focus:bg-white/8 transition-all" />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300" aria-label="مسح البحث">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Conversations list */}
      <nav className="flex-1 overflow-y-auto px-3 pb-2" aria-label="المحادثات السابقة">
        {groups.length === 0 ? (
          <p className="text-gray-500 text-xs text-center mt-8">{searchQuery ? 'لا توجد نتائج' : 'لا توجد محادثات سابقة'}</p>
        ) : (
          groups.map((g) => (
            <div key={g.label} className="mb-3">
              <p className="text-[10px] font-medium text-gray-500 px-2 mb-1.5 uppercase tracking-wider">{g.label}</p>
              {g.items.map((c) => (
                <Link key={c.id} href={`/chat/${c.id}`} className={clsx('group flex items-center justify-between px-3 py-2 rounded-lg text-sm mb-0.5 transition-all duration-200', currentConvId === c.id ? 'sidebar-active' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200')} aria-current={currentConvId === c.id ? 'page' : undefined}>
                  {editingId === c.id ? (
                    <input ref={editInputRef} type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} onBlur={saveTitle} onKeyDown={handleEditKeyDown} onClick={(e) => e.preventDefault()} className="flex-1 bg-white/10 border border-primary-500/30 rounded px-2 py-0.5 text-xs text-gray-200 focus:outline-none focus:border-primary-400" aria-label="تعديل عنوان المحادثة" />
                  ) : (
                    <span className="truncate flex-1" onDoubleClick={(e) => startEditing(c, e)}>
                      <svg className="w-3.5 h-3.5 inline ml-1.5 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
                      {c.title || 'محادثة جديدة'}
                    </span>
                  )}
                  {editingId !== c.id && (
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={(e) => startEditing(c, e)} className="p-1 rounded hover:bg-white/10 hover:text-primary-300 transition-all" title="تعديل العنوان" aria-label="تعديل عنوان المحادثة">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                      </button>
                      <button onClick={(e) => handleDeleteRequest(c.id, e)} className="p-1 rounded hover:bg-red-500/15 hover:text-red-400 transition-all" title="حذف" aria-label="حذف المحادثة">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                      </button>
                    </div>
                  )}
                </Link>
              ))}
            </div>
          ))
        )}
      </nav>

      {/* Tools */}
      <nav className="px-3 py-2 border-t border-white/5" aria-label="أدوات">
        <p className="text-[10px] font-medium text-gray-500 px-2 mb-1.5 uppercase tracking-wider">أدوات</p>
        {[
          { href: '/articles', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253', label: 'استعراض النظام' },
          { href: '/draft', icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z', label: 'صياغة المذكرات' },
          { href: '/deadlines', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z', label: 'حاسبة المهل' },
          { href: '/subscription', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z', label: 'الاشتراك' },
        ].map((t) => (
          <Link key={t.href} href={t.href} className={clsx('flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm mb-0.5 transition-all duration-200', pathname === t.href ? 'sidebar-active' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200')} aria-current={pathname === t.href ? 'page' : undefined}>
            <svg className="w-4 h-4 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={t.icon} /></svg>
            {t.label}
          </Link>
        ))}
      </nav>

      <UsageBar compact />

      {/* User section with dark mode toggle */}
      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-xs font-bold ring-1 ring-gold-400/20">
            {user?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-gray-300 text-xs truncate">{user?.email || ''}</span>
              <SubscriptionBadge />
            </div>
          </div>
          <button onClick={toggleTheme} className="p-1.5 rounded-lg text-gray-500 hover:text-yellow-400 hover:bg-yellow-400/10 transition-all" title={theme === 'dark' ? 'الوضع الفاتح' : 'الوضع الداكن'} aria-label={theme === 'dark' ? 'تبديل إلى الوضع الفاتح' : 'تبديل إلى الوضع الداكن'}>
            {theme === 'dark' ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
            )}
          </button>
          <button onClick={signOut} className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all" title="تسجيل الخروج" aria-label="تسجيل الخروج">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
          </button>
        </div>
      </div>

      {/* Delete confirmation dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setDeleteConfirm(null)}>
          <div className="bg-surface-900 border border-white/10 rounded-2xl p-6 mx-4 max-w-sm w-full shadow-2xl" onClick={(e) => e.stopPropagation()} role="alertdialog" aria-labelledby="delete-title" aria-describedby="delete-desc">
            <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </div>
            <h3 id="delete-title" className="text-white text-center font-bold mb-2">حذف المحادثة</h3>
            <p id="delete-desc" className="text-gray-400 text-sm text-center mb-5">هل أنت متأكد من حذف هذه المحادثة؟ لا يمكن التراجع عن هذا الإجراء.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 py-2.5 rounded-xl bg-white/5 border border-white/10 text-gray-300 text-sm hover:bg-white/10 transition-all">إلغاء</button>
              <button onClick={handleDeleteConfirm} className="flex-1 py-2.5 rounded-xl bg-red-500 text-white text-sm font-medium hover:bg-red-600 transition-all">حذف</button>
            </div>
          </div>
        </div>
      )}
    </>
  );

  return (
    <>
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 glass-card-dark z-40 flex items-center justify-between px-4">
        <Link href="/chat" className="flex items-center gap-2" aria-label="الرئيسية">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" /></svg>
          </div>
          <span className="text-white font-bold text-sm font-heading">Sanad AI</span>
        </Link>
        <button onClick={() => setMobileOpen(!mobileOpen)} className="p-2 rounded-lg text-gray-300 hover:bg-white/5 transition-colors" aria-label={mobileOpen ? 'إغلاق القائمة' : 'فتح القائمة'} aria-expanded={mobileOpen}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
      </div>

      {mobileOpen && <div className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={() => setMobileOpen(false)} />}

      <aside className={clsx('fixed top-0 right-0 h-full w-72 glass-card-dark z-50 flex flex-col transition-transform duration-300', 'lg:translate-x-0', mobileOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0')} aria-label="القائمة الجانبية">
        {sidebarContent}
      </aside>
    </>
  );
}
