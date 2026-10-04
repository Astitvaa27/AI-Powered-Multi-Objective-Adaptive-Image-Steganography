import { useSearchParams } from "react-router-dom";
import { LockKeyhole, ScanSearch } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnalysesList, type AnalysisFilter } from "@/components/history/AnalysesList";
import { HiddenMessagesList } from "@/components/history/HiddenMessagesList";
import { Card } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";

type HistoryTab = "hidden" | "analyses";

/** Tab and filter live in the URL so they survive refreshes and links. */
export function HistoryPage() {
  const [params, setParams] = useSearchParams();

  const tab: HistoryTab = params.get("tab") === "analyses" ? "analyses" : "hidden";
  const filterParam = params.get("result");
  const filter: AnalysisFilter = filterParam === "STEGO" || filterParam === "CLEAN" ? filterParam : "";
  const page = Math.max(0, Number(params.get("page") ?? 0) || 0);

  const update = (next: Record<string, string | null>) =>
    setParams(
      (current) => {
        for (const [key, value] of Object.entries(next)) {
          if (value === null || value === "") current.delete(key);
          else current.set(key, value);
        }
        return current;
      },
      { replace: true },
    );

  return (
    <AppLayout title="History" description="Everything you've hidden and analyzed.">
      <Card>
        <Tabs
          label="History type"
          value={tab}
          onChange={(value) => update({ tab: value === "hidden" ? null : value, result: null, page: null })}
          className="px-5"
          options={[
            { value: "hidden", label: "Hidden messages", icon: <LockKeyhole className="h-4 w-4" aria-hidden /> },
            { value: "analyses", label: "Image analyses", icon: <ScanSearch className="h-4 w-4" aria-hidden /> },
          ]}
        />
        {tab === "hidden" ? (
          <HiddenMessagesList />
        ) : (
          <AnalysesList
            filter={filter}
            onFilterChange={(value) => update({ result: value || null, page: null })}
            page={page}
            onPageChange={(value) => update({ page: value ? String(value) : null })}
          />
        )}
      </Card>
    </AppLayout>
  );
}
