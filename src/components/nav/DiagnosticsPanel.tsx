"use client";

import { useState } from "react";
import clsx from "clsx";
import type { BackendHealth } from "@/lib/data/health";

const OK = "●";
const BAD = "●";

function Row({ label, ok, value }: { label: string; ok: boolean; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <span className="text-text-dim">{label}</span>
      <span className={clsx("flex items-center gap-1.5", ok ? "text-pass" : "text-fail")}>
        <span aria-hidden>{ok ? OK : BAD}</span>
        {value}
      </span>
    </div>
  );
}

/**
 * Operator/jury transparency panel (brief §26): proves the app is backed
 * by a real running backend rather than static UI, without dominating the
 * product surface — collapsed to a small corner badge by default.
 */
export default function DiagnosticsPanel({ health }: { health: BackendHealth }) {
  const [open, setOpen] = useState(false);
  const backendUp = health.status === "ok";

  return (
    <div className="fixed bottom-3 right-3 z-[70] font-mono text-[11px]">
      {open ? (
        <div className="mb-2 w-[240px] border border-ring bg-surface p-3.5 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
          <div className="mb-2 flex items-center justify-between">
            <span className="uppercase tracking-[0.5px] text-text-dim">Diagnostics</span>
            <button type="button" onClick={() => setOpen(false)} className="text-text-dim">
              ×
            </button>
          </div>
          <Row label="Backend" ok={backendUp} value={backendUp ? "CONNECTED" : "ERROR"} />
          <Row label="Database" ok={health.database === "connected"} value={health.database.toUpperCase()} />
          <Row label="Data mode" ok value={health.dataMode.toUpperCase()} />
          <Row
            label="AI provider"
            ok
            value={health.aiProvider === "none" ? "NONE" : health.aiProviderConfigured ? "ANTHROPIC (LIVE)" : "ANTHROPIC (NO KEY)"}
          />
          <Row label="Audio" ok={health.recordingsAvailable > 0} value={`${health.recordingsAvailable} AVAILABLE`} />
          <Row label="Sandbox" ok={health.sandboxConfigured} value={health.sandboxConfigured ? "CONFIGURED" : "NOT CONFIGURED"} />
        </div>
      ) : null}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          "flex items-center gap-1.5 border border-ring bg-surface px-2.5 py-1.5 text-text-dim",
          !backendUp && "border-fail text-fail",
        )}
      >
        <span aria-hidden>{backendUp ? OK : BAD}</span>
        diag
      </button>
    </div>
  );
}
