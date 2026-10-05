import type { NextConfig } from 'next';
const config: NextConfig = {
  experimental: { proxyTimeout: 200000 },
  async rewrites() { return [{ source: '/api/backend/:path*', destination: `${process.env.BACKEND_URL || 'http://api:8000'}/:path*` }]; }
};
export default config;
