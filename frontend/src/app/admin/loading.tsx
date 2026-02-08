import { LoadingAnimation } from "@/components/shared/LoadingAnimation";

export default function AdminLoading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <LoadingAnimation label="Loading admin dashboard…" />
    </div>
  );
}
