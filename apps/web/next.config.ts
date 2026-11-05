import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Company logos and task evidence are uploaded through Server Actions before
  // being forwarded to the API (which accepts up to 10 MB). The Next.js
  // default is 1 MB, which surfaced as a generic 500 after saving settings.
  experimental: {
    serverActions: {
      bodySizeLimit: "12mb",
    },
  },
};

export default nextConfig;
