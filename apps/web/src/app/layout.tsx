import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Parent Plus Coach",
  description: "Parent Plus coach companion",
  appleWebApp: {
    capable: true,
    title: "Parent Plus",
    statusBarStyle: "default",
  },
  icons: { apple: "/icons/parentplus-180.png" },
};

export const viewport: Viewport = {
  themeColor: "#1F6F6B",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
