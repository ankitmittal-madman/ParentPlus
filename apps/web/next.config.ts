import type { NextConfig } from "next";
import founderTesting from "./founder-testing.config.json";

const nextConfig: NextConfig = {
  // Vercel is currently the founder testing app. Launch is an explicit later stage.
  ...(process.env.VERCEL === "1" && process.env.PARENTPLUS_APP_STAGE !== "launch" ? { env: founderTesting } : {}),
  devIndicators: false,
  allowedDevOrigins: [
    "3000-cs-867171362224-default.cs-asia-southeast1-seal.cloudshell.dev",
  ],
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
