import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Jojo Bot — Purification Expert",
  description: "AI-powered purification assistant for Cytiva ÄKTA systems and Nurix protein SOPs",
  icons: { icon: "/jojo-avatar.png" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-gray-50" style={{ fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
