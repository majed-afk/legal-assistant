/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // In production with NEXT_PUBLIC_API_URL, no rewrites needed (direct API calls)
    // In dev, proxy /api/* to local backend
    if (process.env.NEXT_PUBLIC_API_URL) {
      return [];
    }
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
