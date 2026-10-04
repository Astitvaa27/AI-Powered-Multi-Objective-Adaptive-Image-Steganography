import { Link } from "react-router-dom";
import { ScanSearch } from "lucide-react";
import { listSessions } from "@/api/steganalysis";
import { useAsync } from "@/hooks/useAsync";
import { formatDateTime, formatPercent } from "@/lib/format";
import { Badge, statusLabel, statusTone } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Pagination } from "@/components/ui/Pagination";
import { SegmentedControl } from "@/components/ui/Tabs";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";

const PAGE_SIZE = 20;

export type AnalysisFilter = "" | "STEGO" | "CLEAN";

function Verdict({ predictedClass }: { predictedClass: string | null }) {
  if (!predictedClass) return <span className="text-muted">—</span>;
  return predictedClass === "STEGO" ? (
    <Badge tone="stego">Likely hidden data</Badge>
  ) : (
    <Badge tone="clean">Nothing detected</Badge>
  );
}

export function AnalysesList({
  filter,
  onFilterChange,
  page,
  onPageChange,
}: {
  filter: AnalysisFilter;
  onFilterChange: (filter: AnalysisFilter) => void;
  page: number;
  onPageChange: (page: number) => void;
}) {
  const { data, loading, error, reload } = useAsync(
    () =>
      listSessions({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        predicted_class: filter || undefined,
      }),
    [page, filter],
    "Couldn't load your analyses.",
  );

  return (
    <>
      <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-3">
        <span className="text-sm text-muted">Show</span>
        <SegmentedControl
          label="Filter analyses by result"
          value={filter}
          onChange={onFilterChange}
          options={[
            { value: "", label: "All" },
            { value: "STEGO", label: "Likely hidden data" },
            { value: "CLEAN", label: "Nothing detected" },
          ]}
        />
      </div>

      {loading && !data && <SkeletonRows rows={6} />}
      {error && <ErrorState message={error} onRetry={() => void reload()} />}

      {!error && data && data.items.length === 0 && (
        <EmptyState
          icon={<ScanSearch className="h-5 w-5" />}
          title={filter ? "No analyses match this filter" : "No analyses yet"}
          description={
            filter
              ? "Try showing all analyses."
              : "Analyze an image to see whether it's likely to contain hidden data."
          }
          action={!filter && <ButtonLink to="/analyze">Analyze an image</ButtonLink>}
        />
      )}

      {!error && data && data.items.length > 0 && (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-xs text-muted">
                <tr>
                  <th scope="col" className="px-5 py-2.5 font-medium">Date</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Image</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Result</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Probability of hidden data</th>
                  <th scope="col" className="px-5 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.items.map((session) => (
                  <tr key={session.analysis_session_id} className="hover:bg-elevated/50">
                    <td className="whitespace-nowrap px-5 py-3 text-muted">{formatDateTime(session.created_at)}</td>
                    <td className="max-w-[16rem] px-3 py-3">
                      <Link
                        to={`/history/analyses/${session.analysis_session_id}`}
                        className="block truncate font-medium text-accent hover:underline"
                        title={session.image_filename ?? undefined}
                      >
                        {session.image_filename ?? "Unnamed image"}
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      <Verdict predictedClass={session.predicted_class} />
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-fg">
                      {formatPercent(session.probabilities?.STEGO ?? null, 1)}
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={statusTone(session.status)} title={session.error_message ?? undefined}>
                        {statusLabel(session.status)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="divide-y divide-line md:hidden">
            {data.items.map((session) => (
              <li key={session.analysis_session_id}>
                <Link
                  to={`/history/analyses/${session.analysis_session_id}`}
                  className="block space-y-1.5 px-4 py-4 hover:bg-elevated/50"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="min-w-0 truncate text-sm font-medium text-fg">
                      {session.image_filename ?? "Unnamed image"}
                    </span>
                    <Verdict predictedClass={session.predicted_class} />
                  </div>
                  <p className="text-xs text-muted">
                    {formatDateTime(session.created_at)} · hidden-data probability{" "}
                    {formatPercent(session.probabilities?.STEGO ?? null, 1)}
                  </p>
                </Link>
              </li>
            ))}
          </ul>

          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={onPageChange} />
        </>
      )}
    </>
  );
}
