'use client';

import { useState, useEffect } from 'react';
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
      <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-2">📖 استعراض النظام</h1>
      <p className="text-gray-500 text-sm mb-4 sm:mb-6">ابحث في مواد الأنظمة الثلاثة</p>

      {/* Search */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 sm:p-4 mb-4 sm:mb-6">
        <div className="flex gap-2 sm:gap-3 mb-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="ابحث في النظام... مثال: شروط الخلع"
            className="flex-1 px-3 sm:px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-4 sm:px-6 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 whitespace-nowrap"
          >
            {loading ? 'جاري...' : 'بحث'}
          </button>
        </div>

        {/* Topic filters */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedTopic('')}
            className={`px-3 py-1 rounded-full text-xs ${
              !selectedTopic ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            الكل
          </button>
          {topics.map((t) => (
            <button
              key={t.name}
              onClick={() => setSelectedTopic(t.name)}
              className={`px-3 py-1 rounded-full text-xs ${
                selectedTopic === t.name
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {t.name} ({t.count})
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {results.map((article, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-3 sm:p-5 hover:shadow-md transition-shadow">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-2 py-0.5 bg-primary-50 text-primary-700 rounded text-xs font-medium">
                {article.topic}
              </span>
              <span className="px-2 py-0.5 bg-gray-50 text-gray-500 rounded text-xs">
                {article.chapter}
              </span>
              <span className="text-xs text-gray-400 mr-auto">
                تطابق: {Math.round(article.similarity * 100)}%
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-2">{article.section}</p>
            <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{article.text}</p>
          </div>
        ))}

        {results.length === 0 && query && !loading && (
          <div className="text-center py-12 text-gray-400">
            لم يتم العثور على نتائج. حاول تعديل كلمات البحث.
          </div>
        )}
      </div>
    </div>
  );
}
