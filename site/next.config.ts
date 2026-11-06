import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Builds .next/standalone with a minimal server.js, which is what runs on Cloud Run.
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
