/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output only when building a distributable package.
  // Set BUILD_STANDALONE=true in the environment (the build-package.bat does this).
  // In normal dev/local use this stays undefined so `npm start` works as usual.
  output: process.env.BUILD_STANDALONE === "true" ? "standalone" : undefined,

  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
