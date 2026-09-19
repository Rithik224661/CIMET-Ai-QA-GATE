import type { ReactNode } from "react";
import Rail from "@/components/nav/Rail";
import DiagnosticsPanel from "@/components/nav/DiagnosticsPanel";
import { ALL_RETAILERS, getQueueBadgeCount } from "@/lib/data/queue";
import { getHealth } from "@/lib/data/health";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const [queueBadgeCount, health] = await Promise.all([getQueueBadgeCount(ALL_RETAILERS), getHealth()]);

  return (
    <div className="flex min-h-screen flex-col rail:flex-row">
      <Rail queueBadgeCount={queueBadgeCount} />
      <main className="flex min-w-0 flex-1 flex-col">{children}</main>
      <DiagnosticsPanel health={health} />
    </div>
  );
}
