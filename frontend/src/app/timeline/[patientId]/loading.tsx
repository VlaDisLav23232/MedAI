import { LoadingAnimation } from "@/components/shared/LoadingAnimation";

export default function TimelineLoading() {
  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark flex items-center justify-center">
      <div className="text-center">
        <LoadingAnimation label="Loading patient timeline…" variant="orbital" />
        <p className="text-xs text-gray-400 mt-3">
          Fetching longitudinal health records
        </p>
      </div>
    </div>
  );
}
