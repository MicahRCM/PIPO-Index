import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Pin the workspace root to this app directory. The repo has lockfiles in
  // both the parent (legacy site) and here; without this, Next infers the
  // parent as root, which breaks file tracing / Vercel deploys of `web/`.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
