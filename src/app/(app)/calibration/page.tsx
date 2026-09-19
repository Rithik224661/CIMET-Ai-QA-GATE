import ViewShell from "@/components/layout/ViewShell";
import CalKpis from "@/components/calibration/CalKpis";
import ConfidenceHistogram from "@/components/calibration/ConfidenceHistogram";
import DisagreementBars from "@/components/calibration/DisagreementBars";
import { getCalibrationMetrics } from "@/lib/data/calibration";

export const metadata = { title: "Calibration · CIMET QA Gate" };

export default async function CalibrationPage() {
  const { kpis, confidenceBuckets, confidenceBucketMax, disagreements, disagreementMax, sampledCallsTotal, sampledDisagreementsTotal } =
    await getCalibrationMetrics();

  return (
    <ViewShell crumb="Assurance" title="Model calibration">
      <div className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-chip-bg px-2.5 py-1">
        <span className="block size-1.5 rounded-full bg-review" />
        <span className="font-mono text-xs uppercase text-text-muted">Synthetic calibration data</span>
      </div>

      <CalKpis kpis={kpis} />

      <div className="mt-4 grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
        <ConfidenceHistogram buckets={confidenceBuckets} max={confidenceBucketMax} />
        <DisagreementBars
          categories={disagreements}
          max={disagreementMax}
          sampledCallsTotal={sampledCallsTotal}
          disagreementsTotal={sampledDisagreementsTotal}
        />
      </div>
    </ViewShell>
  );
}
