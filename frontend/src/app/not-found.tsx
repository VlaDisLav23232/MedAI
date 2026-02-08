import Link from "next/link";
import { Search } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="w-16 h-16 rounded-2xl bg-brand-500/10 flex items-center justify-center mx-auto mb-4">
          <Search size={32} className="text-brand-500" />
        </div>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
          Page Not Found
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          The page you&apos;re looking for doesn&apos;t exist or the resource has
          been moved.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition shadow-lg shadow-brand-500/25 active:scale-[0.98]"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
