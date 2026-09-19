import { Suspense } from "react";
import TopBarControls from "./TopBarControls";

export default function TopBar({ crumb, title }: { crumb: string; title: string }) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-ring bg-bg px-4 py-4 rail:px-[clamp(16px,2.4vw,28px)]">
      <div className="min-w-0">
        <div className="font-mono text-[11px] uppercase tracking-[1px] text-text-dim">{crumb}</div>
        <h1 className="mt-0.5 overflow-hidden text-ellipsis whitespace-nowrap text-lg font-medium tracking-[-0.5px]">{title}</h1>
      </div>
      <Suspense fallback={null}>
        <TopBarControls />
      </Suspense>
    </div>
  );
}
