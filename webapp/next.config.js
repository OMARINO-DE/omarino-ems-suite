/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'standalone',
  
  // Environment variables
  env: {
    // Client-side API URL (public internet)
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://ems-back.omarino.net',
    // Server-side API URL (internal Docker network) - only available on server
    INTERNAL_API_URL: process.env.INTERNAL_API_URL || 'http://omarino-gateway:8080',
  },
  
  // Server-side rendering configuration
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  
  // Remove rewrites as we're handling API calls directly in code
  // This allows us to use different URLs for client/server
}

module.exports = nextConfig
