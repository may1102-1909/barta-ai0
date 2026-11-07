import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "BARTA AI · Voice Agent Workspace",
  description: "Outbound voice agent console.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f172a",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@300;400;500;600;700;800;900&family=Noto+Serif+Devanagari:wght@400;600;700;800&display=swap"
        />
      </head>
      <body className="min-h-screen bg-white font-sans antialiased text-slate-900 selection:bg-navy-900 selection:text-white">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
