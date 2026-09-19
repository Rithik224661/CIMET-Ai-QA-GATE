import Link from "next/link";
import { buttonClass } from "@/components/ui/Button";

/**
 * Themed 404 (brief: "no owring things" / broken-looking pages are a real
 * finding). Without this, Next's built-in not-found fallback renders with
 * its own light-mode styling regardless of the app's dark theme — jarring
 * and inconsistent with every other view. Reached from notFound() in
 * sales/[leadId]/page.tsx for an unknown lead id, or any unmatched route
 * under the app shell.
 */
export default function NotFound() {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <div className="max-w-[420px] border border-ring bg-surface p-8 text-center">
        <div className="font-mono text-[28px] text-text-dim">404</div>
        <div className="mt-3 text-[15px] text-text-2">Not found</div>
        <p className="mx-auto mt-2 text-[13px] leading-relaxed text-text-muted">
          That page or lead doesn&apos;t exist in this demo dataset.
        </p>
        <Link href="/dashboard" className={buttonClass("primary", "mt-5 justify-center")}>
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
