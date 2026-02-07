import { LoadingAnimation } from "@/components/shared/LoadingAnimation";

export default function CaseLoading() {
  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark flex items-center justify-center">
      <div className="text-center">
        <LoadingAnimation label="Loading case report…" variant="orbital" />
        <p className="text-xs text-gray-400 mt-3">
          Fetching AI analysis and findings
        </p>
      </div>
    </div>
  );
}
