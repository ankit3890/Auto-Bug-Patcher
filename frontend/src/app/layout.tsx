import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "AutoBug AI — Autonomous Bug Fixer",
  description:
    "AutoBug AI autonomously detects bugs, performs root cause analysis, generates validated code fixes, and opens GitHub Pull Requests.",
  keywords: ["bug fix", "AI", "automated testing", "code review", "LangGraph"],
  openGraph: {
    title: "AutoBug AI",
    description: "Autonomous bug detection and resolution platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen bg-surface-950 text-slate-100 antialiased">
        {/* Background grid */}
        <div
          className="fixed inset-0 pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,.025) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
        <Navbar />
        <main className="relative z-10">{children}</main>
      </body>
    </html>
  );
}
