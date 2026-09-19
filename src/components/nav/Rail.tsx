"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { DEFAULT_LEAD_ID } from "@/lib/fixtures/leads";

interface NavItem {
  id: string;
  num: string;
  label: string;
  href: string;
  matches: (pathname: string) => boolean;
}

function currentLeadId(pathname: string): string {
  const m = /^\/(?:sales|audit)\/([^/]+)/.exec(pathname);
  return m ? m[1] : DEFAULT_LEAD_ID;
}

export default function Rail({ queueBadgeCount }: { queueBadgeCount: number }) {
  const pathname = usePathname();
  const leadId = currentLeadId(pathname);

  const items: NavItem[] = [
    { id: "dashboard", num: "01", label: "Dashboard", href: "/dashboard", matches: (p) => p.startsWith("/dashboard") },
    { id: "queue", num: "02", label: "QA Queue", href: "/queue", matches: (p) => p.startsWith("/queue") },
    { id: "sale", num: "03", label: "Sales", href: `/sales/${leadId}`, matches: (p) => p.startsWith("/sales") },
    { id: "calibration", num: "04", label: "Calibration", href: "/calibration", matches: (p) => p.startsWith("/calibration") },
    { id: "rules", num: "05", label: "Rules", href: "/rules", matches: (p) => p.startsWith("/rules") },
    { id: "audit", num: "06", label: "Audit", href: `/audit/${leadId}`, matches: (p) => p.startsWith("/audit") },
  ];

  return (
    <aside
      className={clsx(
        "flex-none border-ring bg-surface",
        "flex flex-col gap-3 border-b px-3 py-3.5",
        "rail:sticky rail:top-0 rail:h-screen rail:w-[208px] rail:flex-col rail:gap-[18px] rail:overflow-auto rail:border-b-0 rail:border-r rail:px-0 rail:py-5",
      )}
    >
      <div className="flex items-center gap-2.5 px-2 pb-1">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" className="flex-none">
          <rect x="0.5" y="0.5" width="17" height="17" stroke="#fff" />
          <rect x="5" y="5" width="8" height="8" fill="#52a8ff" />
        </svg>
        <span className="text-[15px] font-medium tracking-[-0.3px]">
          Verity<span className="text-text-muted">Gate</span>
        </span>
      </div>

      <nav aria-label="Primary" className="flex gap-1 overflow-x-auto rail:flex-col rail:overflow-visible">
        {items.map((item) => {
          const active = item.matches(pathname);
          return (
            <Link
              key={item.id}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={clsx(
                "flex w-full items-center gap-2.5 whitespace-nowrap border-l-2 px-3 py-2.5 font-sans text-[13px]",
                active ? "border-accent bg-surface-2 text-text" : "border-transparent text-text-muted hover:bg-surface-2 hover:text-text",
              )}
            >
              <span className="w-4 flex-none font-mono text-[11px] text-text-dim">{item.num}</span>
              <span>{item.label}</span>
              {item.id === "queue" ? (
                <span className="ml-auto rounded-full bg-chip-bg px-2 py-px font-mono text-[11px] text-text-muted">
                  {queueBadgeCount}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto hidden px-3.5 rail:block">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-chip-bg px-2.5 py-1">
          <span className="block size-1.5 rounded-full bg-review" />
          <span className="font-mono text-[11px] uppercase tracking-[0.5px] text-text-muted">Demo data</span>
        </span>
        <p className="mt-3 font-mono text-[11px] leading-relaxed text-text-dim">
          Synthetic leads and sanitised transcripts. No customer PII.
        </p>
      </div>
    </aside>
  );
}
