import type { ReactNode } from "react";
import Rail from "@/components/nav/Rail";
import { ALL_RETAILERS, getQueueBadgeCount } from "@/lib/data/queue";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const queueBadgeCount = await getQueueBadgeCount(ALL_RETAILERS);

  return (
    <div className="flex min-h-screen flex-col rail:flex-row">
      <Rail queueBadgeCount={queueBadgeCount} />
      <main className="flex min-w-0 flex-1 flex-col">{children}</main>
    </div>
  );
}
