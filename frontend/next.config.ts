import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname),
  eslint: {
    ignoreDuringBuilds: true,
  },
  webpack: (config) => {
    // react-pdf / pdfjs-dist relies on canvas in node environments; not needed client-side.
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
