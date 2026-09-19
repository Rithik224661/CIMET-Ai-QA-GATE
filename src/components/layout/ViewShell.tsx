import type { ReactNode } from "react";
import TopBar from "@/components/nav/TopBar";

/** Sticky top bar + scrollable content region — the shell every view sits
 * inside. Each page supplies its own crumb/title (they vary per view). */
export default function ViewShell({
  crumb,
  title,
  children,
}: {
  crumb: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <>
      <TopBar crumb={crumb} title={title} />
      <div className="qa-scroll min-h-0 flex-1 overflow-auto p-4 pb-16 rail:p-[clamp(16px,2.4vw,28px)]">{children}</div>
    </>
  );
}
