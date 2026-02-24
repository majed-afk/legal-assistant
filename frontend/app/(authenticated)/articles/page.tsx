'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { searchArticles, getTopics } from '@/lib/api';

interface Article {
  text: string;
  chapter: string;
  section: string;
  topic: string;
  similarity: number;
}

interface Topic {
  name: string;
  count: number;
}

export default function ArticlesPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Article[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getTopics()
      .then((data) => setTopics(data.topics))
      .catch(() => {});
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await searchArticles(query, selectedTopic || undefined);
      setResults(data.results);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold gradient-text font-heading">استعراض النظام</h1>
            <p className="text-gray-500 text-sm">ابحث في مواد الأنظمة الثلاثة</p>
          </div>
        </div>
      </motion.div>

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="glass-card p-4 sm:p-5 mb-5"
      >
        <div className="flex gap-2 sm:gap-3 mb-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="ابحث في النظام... مثال: شروط الخلع"
            className="flex-1 px-3 sm:px-4 py-2.5 border border-gray-200/80 bg-white/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-300 transition-all"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-5 sm:px-6 py-2.5 bg-gradient-to-l from-primary-500 to-primary-600 text-white rounded-xl text-sm font-medium hover:shadow-glow active:scale-[0.98] disabled:opacity-50 whitespace-nowrap transition-all duration-300"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                جاري...
              </span>
            ) : 'بحث'}
          </button>
        </div>

        {/* Topic filters */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedTopic('')}
            className={clsx(
              'px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200',
              !selectedTopic
                ? 'bg-gradient-to-l from-primary-500 to-primary-600 text-white shadow-sm'
                : 'bg-gray-100/80 text-gray-600 hover:bg-gray-200/80'
            )}
          >
            الكل
          </button>
          {topics.map((t) => (
            <button
              key={t.name}
              onClick={() => setSelectedTopic(t.name)}
              className={clsx(
                'px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200',
                selectedTopic === t.name
                  ? 'bg-gradient-to-l from-primary-500 to-primary-600 text-white shadow-sm'
                  : 'bg-gray-100/80 text-gray-600 hover:bg-gray-200/80'
              )}
            >
              {t.name} ({t.count})
            </button>
          ))}
        </div>
      </motion.div>

      {/* Results */}
      <div className="space-y-4">
        {results.map((article, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.05 }}
            className="glass-card p-4 sm:p-5 hover:shadow-elevated hover:-translate-y-0.5 transition-all duration-300"
          >
            <div className="flex flex-wrap items-center gap-2 mb-2.5">
              <span className="px-2.5 py-0.5 bg-primary-50 text-primary-700 rounded-lg text-xs font-medium border border-primary-100/50">
                {article.topic}
              </span>
              <span className="px-2.5 py-0.5 bg-gray-50 text-gray-500 rounded-lg text-xs border border-gray-100">
                {article.chapter}
              </span>
              <span className="text-xs text-gray-400 mr-auto flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                تطابق: {Math.round(article.similarity * 100)}%
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-2">{article.section}</p>
            <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{article.text}</p>
          </motion.div>
        ))}

        {results.length === 0 && query && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-16"
          >
            <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-gray-400 text-sm">لم يتم العثور على نتائج. حاول تعديل كلمات البحث.</p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
