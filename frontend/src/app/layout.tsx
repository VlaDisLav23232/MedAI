import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { AuthProvider } from "@/providers/AuthProvider";
import { QueryProvider } from "@/providers/QueryProvider";
import { Navbar } from "@/components/layout/Navbar";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

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
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-brand-500 focus:text-white focus:text-sm focus:font-medium"
        >
          Skip to main content
        </a>
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              <Navbar />
              <ErrorBoundary label="Application">
                <div id="main-content">{children}</div>
              </ErrorBoundary>
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
