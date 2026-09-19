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
        <Button variant="primary">Re-request recording</Button>
        <Button variant="secondary">Route to manual QA</Button>
      </div>
      <div className="mt-5 font-mono text-[11px] text-text-dim">
        ingest_error · {ingestError.code} · retry {ingestError.retry} · {ingestError.at}
      </div>
    </div>
  );
}
