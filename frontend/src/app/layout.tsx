import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { Navbar } from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "MedAI Clinical Co-Pilot",
  description:
    "An Agentic Intelligence Layer for Modern Healthcare — Multi-modal medical AI assistant powered by MedGemma & Claude.",
  keywords: ["medical AI", "clinical co-pilot", "MedGemma", "healthcare", "diagnostic AI"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-white dark:bg-surface-dark text-gray-900 dark:text-gray-100 font-sans">
        <ThemeProvider>
          <Navbar />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
