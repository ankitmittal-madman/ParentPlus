import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Parent Plus",
    short_name: "Parent Plus",
    description: "Your classes, family updates and learning journey.",
    start_url: "/login",
    scope: "/",
    display: "standalone",
    background_color: "#F3F5F1",
    theme_color: "#1F6F6B",
    icons: [
      {
        src: "/icons/parentplus-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/parentplus-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
