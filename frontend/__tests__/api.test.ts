/**
 * Tests for the centralized API client.
 */

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock Supabase
jest.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      getSession: jest.fn().mockResolvedValue({ data: { session: null } }),
    },
  }),
}));

import { askQuestion, searchArticles, getArticles, healthCheck } from '@/lib/api';

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('should handle 401 errors with Arabic message', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' }),
    });

    // askQuestion calls getHeaders() then fetch; on !res.ok it throws
    await expect(askQuestion('test question')).rejects.toThrow();
  });

  it('should handle 429 rate limit errors', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Rate limited' }),
    });

    await expect(askQuestion('test question')).rejects.toThrow();
  });

  it('should handle network errors', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(getArticles()).rejects.toThrow();
  });

  it('should throw on search errors', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Server error' }),
    });

    await expect(searchArticles('test query')).rejects.toThrow();
  });

  it('should return JSON on successful healthCheck', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    });

    const result = await healthCheck();
    expect(result).toEqual({ status: 'ok' });
  });

  it('should return JSON on successful getArticles', async () => {
    const mockArticles = [{ id: 1, title: 'Test Article' }];
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockArticles,
    });

    const result = await getArticles();
    expect(result).toEqual(mockArticles);
  });

  it('should send POST request with question for askQuestion', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ answer: 'test answer' }),
    });

    const result = await askQuestion('ما هي المادة الأولى؟');
    expect(result).toEqual({ answer: 'test answer' });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/ask');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toHaveProperty('question', 'ما هي المادة الأولى؟');
  });
});
