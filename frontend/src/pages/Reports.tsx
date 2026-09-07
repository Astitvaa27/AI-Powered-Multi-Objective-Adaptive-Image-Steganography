import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, FileBarChart2, Filter } from "lucide-react";
import { ApiError } from "@/api/client";
import { listSessions } from "@/api/steganalysis";
import type { AnalysisSessionSummary } from "@/api/types";
import { AppLayout } from "@/components/layout/AppLayout";
import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/Progress";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { cn } from "@/lib/cn";
import { formatDateTime, formatMs, formatPercent, shortId } from "@/lib/format";

const PAGE_SIZE = 20;

const FILTERS = [
  { id: "", label: "All" },
  { id: "STEGO", label: "Stego" },
  { id: "CLEAN", label: "Clean" },
] as const;

export function ReportsPage() {
  const [sessions, setSessions] = useState<AnalysisSessionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await listSessions({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        predicted_class: filter || undefined,
      });

      setSessions(result.items);
      setTotal(result.total);
    } catch (exception) {
      setError(
        exception instanceof ApiError
          ? exception.message
          : "Unable to load analysis history.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);

  return (
    <AppLayout
      title="Reports"
      subtitle="Every steganalysis session recorded for your account"
    >
      <Card>
        <CardHeader
          title="Analysis history"
          description={
            total > 0
              ? `${total} session${total === 1 ? "" : "s"} recorded`
              : undefined
          }
          icon={<FileBarChart2 className="h-4 w-4" />}
          actions={
            <div className="flex items-center gap-1 rounded-lg bg-elevated p-1">
              <Filter className="ml-1.5 h-3 w-3 text-faint" aria-hidden />
              {FILTERS.map((entry) => (
                <button
                  key={entry.id || "all"}
                  type="button"
                  onClick={() => {
                    setFilter(entry.id);
                    setPage(0);
                  }}
                  aria-pressed={filter === entry.id}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                    filter === entry.id
                      ? "bg-surface text-fg shadow-sm"
                      : "text-muted hover:text-fg",
                  )}
                >
                  {entry.label}
                </button>
              ))}
            </div>
          }
        />

        {loading && <SkeletonRows rows={8} />}

        {!loading && error && (
          <ErrorState message={error} onRetry={() => void load()} />
        )}

        {!loading && !error && sessions.length === 0 && (
          <EmptyState
            icon={<FileBarChart2 className="h-5 w-5" />}
            title={filter ? `No ${filter.toLowerCase()} results` : "No reports yet"}
            description={
              filter
                ? "Try a different filter, or run more analyses."
                : "Analysis sessions appear here once you have run steganalysis on an image."
            }
            action={
              !filter && (
                <Link to="/steganalysis">
                  <Button size="sm">Run steganalysis</Button>
                </Link>
              )
            }
          />
        )}

        {!loading && !error && sessions.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-line text-[11px] uppercase tracking-wide text-faint">
                  <tr>
                    <th scope="col" className="px-5 py-2.5 font-medium">Date &amp; time</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Image</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Type</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Result</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Confidence</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Runtime</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Status</th>
                    <th scope="col" className="px-5 py-2.5 font-medium">Session</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {sessions.map((session) => (
                    <tr
                      key={session.analysis_session_id}
                      className="transition-colors hover:bg-elevated/50"
                    >
                      <td className="whitespace-nowrap px-5 py-2.5 text-muted">
                        {formatDateTime(session.created_at)}
                      </td>
                      <td className="max-w-[15rem] px-3 py-2.5">
                        <Link
                          to={`/reports/${session.analysis_session_id}`}
                          className="block truncate font-medium text-fg hover:text-accent"
                          title={session.image_filename ?? undefined}
                        >
                          {session.image_filename ?? "Unnamed image"}
                        </Link>
                      </td>
                      <td className="px-3 py-2.5 text-muted">
                        {session.analysis_type}
                      </td>
                      <td className="px-3 py-2.5">
                        {session.predicted_class ? (
                          <Badge
                            tone={
                              session.predicted_class === "STEGO"
                                ? "stego"
                                : "clean"
                            }
                          >
                            {session.predicted_class}
                          </Badge>
                        ) : (
                          <span className="text-faint">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        {session.confidence !== null ? (
                          <div className="flex items-center gap-2">
                            <ProgressBar
                              value={session.confidence}
                              tone={
                                session.predicted_class === "STEGO"
                                  ? "stego"
                                  : "clean"
                              }
                              className="w-14"
                            />
                            <span className="font-mono tabular-nums text-muted">
                              {formatPercent(session.confidence, 1)}
                            </span>
                          </div>
                        ) : (
                          <span className="text-faint">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-muted">
                        {formatMs(session.processing_time_ms)}
                      </td>
                      <td className="px-3 py-2.5">
                        <Badge tone={statusTone(session.status)}>
                          {session.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-2.5">
                        <Link
                          to={`/reports/${session.analysis_session_id}`}
                          className="font-mono text-[11px] text-accent hover:underline"
                        >
                          {shortId(session.analysis_session_id)}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {lastPage > 0 && (
              <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
                <p className="text-[11px] text-muted">
                  Showing {page * PAGE_SIZE + 1}–
                  {Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page === 0}
                    onClick={() => setPage((value) => Math.max(0, value - 1))}
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page >= lastPage}
                    onClick={() =>
                      setPage((value) => Math.min(lastPage, value + 1))
                    }
                  >
                    Next
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </AppLayout>
  );
}
