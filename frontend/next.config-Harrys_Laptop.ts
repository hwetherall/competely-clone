import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Force this directory as the Turbopack/Next root (avoids monorepo lockfile confusion) */
  turbopack: { root: "." },
};

export default nextConfig;
