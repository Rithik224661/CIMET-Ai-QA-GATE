import Chip from "@/components/ui/Chip";
import Button from "@/components/ui/Button";
import type { Lead } from "@/lib/types";

export default function IngestError({ leadId, ingestError }: { leadId: string; ingestError: NonNullable<Lead["ingestError"]> }) {
  return (
    <div className="border border-fail bg-surface p-8">
      <Chip tone="fail" dot>
        Processing failed
      </Chip>
      <h2 className="mt-[18px] mb-1.5 text-2xl font-medium tracking-[-1px]">Transcript unavailable for {leadId}</h2>
      <p className="max-w-[520px] text-[13px] leading-relaxed text-text-muted">{ingestError.message}</p>
      <div className="mt-6 flex flex-wrap gap-2.5">
        <Button
          variant="primary"
          disabled
          title="Requires a real CIMET dialler/ingestion integration — not available in this demo (see docs/INTEGRATION.md)"
        >
          Re-request recording
        </Button>
        <Button
          variant="secondary"
          disabled
          title="Requires a real CIMET dialler/ingestion integration — not available in this demo (see docs/INTEGRATION.md)"
        >
          Route to manual QA
        </Button>
      </div>
      <div className="mt-3 font-mono text-[11px] text-text-dim">
        Both actions require the real CIMET ingestion integration (see{" "}
        <code>docs/INTEGRATION.md</code>) — disabled in this demo rather than faking success.
      </div>
      <div className="mt-3 font-mono text-[11px] text-text-dim">
        ingest_error · {ingestError.code} · retry {ingestError.retry} · {ingestError.at}
      </div>
    </div>
  );
}
