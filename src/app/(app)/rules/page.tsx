import ViewShell from "@/components/layout/ViewShell";
import RuleSetList from "@/components/rules/RuleSetList";
import RuleTable from "@/components/rules/RuleTable";
import { getChecksForRuleSet, getRuleSets } from "@/lib/data/rulesets";

export const metadata = { title: "Rules · VerityGate" };

export default async function RulesPage({ searchParams }: { searchParams: Promise<{ set?: string }> }) {
  const sp = await searchParams;
  const ruleSets = await getRuleSets();
  const activeIndex = Math.min(Math.max(Number(sp.set ?? 0) || 0, 0), ruleSets.length - 1);
  const activeRuleSet = ruleSets[activeIndex];
  const checks = await getChecksForRuleSet(activeRuleSet);

  return (
    <ViewShell crumb="Configuration" title="Check library">
      <div className="grid grid-cols-1 items-start gap-4 rail:grid-cols-[280px_minmax(0,1fr)]">
        <RuleSetList ruleSets={ruleSets} activeIndex={activeIndex} />
        <RuleTable ruleSet={activeRuleSet} checks={checks} />
      </div>
    </ViewShell>
  );
}
