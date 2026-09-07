import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Clock,
  Database,
  Gauge,
  Images,
  Layers,
  Radar,
  ShieldHalf,
  Sparkles,
} from "lucide-react";
import { checkDatabaseHealth, checkHealth } from "@/api/auth";
import { getActiveModel, getStats, listSessions } from "@/api/steganalysis";
import { listSteganographySessions } from "@/api/steganography";
import type {
  AnalysisSessionSummary,
  ModelInfo,
  SteganalysisStats,
  SteganographySessionSummary,
} from "@/api/types";
import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { MetricCard } from "@/components/MetricCard";
import { ProgressBar } from "@/components/ui/Progress";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { AppLayout } from "@/components/layout/AppLayout";
import {
  formatMs,
  formatNumber,
  formatPercent,
  formatRelative,
} from "@/lib/format";

interface SystemStatus {
  api: boolean;
  database: boolean;
  model: ModelInfo | null;
  modelError: string | null;
}

export function DashboardPage() {
  const [stats, setStats] = useState<SteganalysisStats | null>(null);
  const [sessions, setSessions] = useState<AnalysisSessionSummary[]>([]);
  const [stegoSessions, setStegoSessions] = useState<
    SteganographySessionSummary[]
  >([]);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    // Each panel degrades independently — one failing endpoint should not
    // blank the whole dashboard.
    const [statsResult, sessionsResult, stegoResult, apiResult, dbResult, modelResult] =
      await Promise.allSettled([
        getStats(),
        listSessions({ limit: 8 }),
        listSteganographySessions({ limit: 5 }),
        checkHealth(),
        checkDatabaseHealth(),
        getActiveModel(),
      ]);

    if (statsResult.status === "fulfilled") setStats(statsResult.value);
    else
      setError(
        statsResult.reason instanceof Error
          ? statsResult.reason.message
          : "Unable to load dashboard statistics.",
      );

    if (sessionsResult.status === "fulfilled")
      setSessions(sessionsResult.value.items);

    if (stegoResult.status === "fulfilled")
      setStegoSessions(stegoResult.value.items);

    setSystem({
      api: apiResult.status === "fulfilled",
      database: dbResult.status === "fulfilled",
      model: modelResult.status === "fulfilled" ? modelResult.value : null,
      modelError:
        modelResult.status === "rejected"
          ? modelResult.reason instanceof Error
            ? modelResult.reason.message
            : "Model unavailable"
          : null,
    });

    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const totalClassified = (stats?.clean_count ?? 0) + (stats?.stego_count ?? 0);

  return (
    <AppLayout
      title="Dashboard"
      subtitle="AI-Powered Multi-Objective Adaptive Image Steganography and Steganalysis Framework"
    >
      {error && !stats && (
        <Card className="mb-6">
          <ErrorState message={error} onRetry={() => void load()} />
        </Card>
      )}

      {/* Quick actions */}
      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <QuickAction
          to="/steganalysis"
          icon={<Radar className="h-4 w-4" />}
          title="Run steganalysis"
          description="Classify an image as CLEAN or STEGO and rank candidate anomaly regions."
        />
        <QuickAction
          to="/steganography"
          icon={<ShieldHalf className="h-4 w-4" />}
          title="Embed a payload"
          description="Hide a message with LSB, DCT or DWT and measure MSE, PSNR and SSIM."
        />
        <QuickAction
          to="/reports"
          icon={<Layers className="h-4 w-4" />}
          title="Browse reports"
          description="Review previous analysis sessions, predictions and feature vectors."
        />
      </div>

      {/* Statistics */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading && !stats ? (
          Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="panel h-[6.5rem] p-4">
              <div className="skeleton h-3 w-24" />
              <div className="skeleton mt-3 h-7 w-16" />
            </div>
          ))
        ) : (
          <>
            <MetricCard
              label="Total analyses"
              value={stats?.total_analyses ?? 0}
              hint={`${stats?.completed_analyses ?? 0} completed · ${
                stats?.failed_analyses ?? 0
              } failed`}
              icon={<Activity className="h-4 w-4" />}
            />
            <MetricCard
              label="Classified STEGO"
              value={stats?.stego_count ?? 0}
              tone="stego"
              hint={
                totalClassified > 0
                  ? `${formatPercent(
                      (stats?.stego_count ?? 0) / totalClassified,
                      0,
                    )} of classified images`
                  : "No classifications yet"
              }
              icon={<Radar className="h-4 w-4" />}
            />
            <MetricCard
              label="Classified CLEAN"
              value={stats?.clean_count ?? 0}
              tone="clean"
              hint={
                totalClassified > 0
                  ? `${formatPercent(
                      (stats?.clean_count ?? 0) / totalClassified,
                      0,
                    )} of classified images`
                  : "No classifications yet"
              }
              icon={<Sparkles className="h-4 w-4" />}
            />
            <MetricCard
              label="Registered images"
              value={stats?.total_images ?? 0}
              hint={`${stats?.total_candidate_regions ?? 0} candidate regions ranked`}
              icon={<Images className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      {/* Main grid */}
      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader
            title="Recent steganalysis"
            description="Latest detection results for your account"
            icon={<Activity className="h-4 w-4" />}
            actions={
              <Link to="/reports">
                <Button variant="ghost" size="sm">
                  View all
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            }
          />

          {loading && sessions.length === 0 && <SkeletonRows rows={5} />}

          {!loading && sessions.length === 0 && (
            <EmptyState
              icon={<Radar className="h-5 w-5" />}
              title="No analyses yet"
              description="Run your first steganalysis to populate this dashboard."
              action={
                <Link to="/steganalysis">
                  <Button size="sm">Open steganalysis</Button>
                </Link>
              }
            />
          )}

          {sessions.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-line text-[11px] uppercase tracking-wide text-faint">
                  <tr>
                    <th scope="col" className="px-5 py-2.5 font-medium">Image</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Result</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Confidence</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Time</th>
                    <th scope="col" className="px-5 py-2.5 font-medium">When</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {sessions.map((session) => (
                    <tr
                      key={session.analysis_session_id}
                      className="transition-colors hover:bg-elevated/50"
                    >
                      <td className="max-w-[16rem] px-5 py-2.5">
                        <Link
                          to={`/reports/${session.analysis_session_id}`}
                          className="block truncate font-medium text-fg hover:text-accent"
                          title={session.image_filename ?? undefined}
                        >
                          {session.image_filename ?? "Unnamed image"}
                        </Link>
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
                          <Badge tone={statusTone(session.status)}>
                            {session.status}
                          </Badge>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <ProgressBar
                            value={session.confidence ?? 0}
                            tone={
                              session.predicted_class === "STEGO"
                                ? "stego"
                                : "clean"
                            }
                            className="w-16"
                          />
                          <span className="font-mono tabular-nums text-muted">
                            {formatPercent(session.confidence, 1)}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 font-mono text-muted">
                        {formatMs(session.processing_time_ms)}
                      </td>
                      <td className="px-5 py-2.5 text-faint">
                        {formatRelative(session.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader
              title="System status"
              description="Backend, database and detection model"
              icon={<Database className="h-4 w-4" />}
            />
            <CardBody className="space-y-3">
              <StatusRow label="API server" ok={system?.api ?? false} />
              <StatusRow label="Database" ok={system?.database ?? false} />
              <StatusRow
                label="Steganalysis model"
                ok={Boolean(system?.model)}
                detail={
                  system?.model
                    ? `${system.model.architecture ?? system.model.name} · v${system.model.version}`
                    : (system?.modelError ?? undefined)
                }
              />

              {system?.model && (
                <div className="rounded-lg border border-line bg-elevated/40 p-3 text-[11px] leading-relaxed text-muted">
                  <p className="font-medium text-fg">{system.model.name}</p>
                  <p className="mt-1">
                    Framework {system.model.framework ?? "—"} · artifact{" "}
                    {system.model.artifact_available
                      ? "present"
                      : "missing on disk"}
                  </p>
                  <p className="mt-1.5">
                    Detection accuracy is payload-dependent; confidence values
                    describe individual classifications rather than overall
                    model accuracy.
                  </p>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Detection averages"
              description="Across your completed sessions"
              icon={<Gauge className="h-4 w-4" />}
            />
            <CardBody className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-wide text-muted">
                  Mean confidence
                </p>
                <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-fg">
                  {formatPercent(stats?.average_confidence, 1)}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wide text-muted">
                  Mean runtime
                </p>
                <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-fg">
                  {formatMs(stats?.average_processing_time_ms)}
                </p>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Steganography activity"
              description="Recent embedding sessions"
              icon={<ShieldHalf className="h-4 w-4" />}
            />

            {stegoSessions.length === 0 ? (
              <EmptyState
                icon={<Clock className="h-5 w-5" />}
                title="No embedding runs yet"
                description="Embed a payload to see quality metrics here."
                className="py-9"
              />
            ) : (
              <ul className="divide-y divide-line">
                {stegoSessions.map((session) => (
                  <li key={session.id} className="px-5 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className="min-w-0 truncate text-xs font-medium text-fg"
                        title={session.cover_image_filename ?? undefined}
                      >
                        {session.cover_image_filename ?? "Cover image"}
                      </span>
                      <Badge tone={statusTone(session.status)}>
                        {session.status}
                      </Badge>
                    </div>
                    <p className="mt-1 font-mono text-[11px] text-faint">
                      PSNR {formatNumber(session.psnr, 2)} dB · SSIM{" "}
                      {formatNumber(session.ssim, 4)} ·{" "}
                      {formatRelative(session.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}

function QuickAction({
  to,
  icon,
  title,
  description,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Link
      to={to}
      className="panel group flex items-start gap-3 p-4 transition-colors hover:border-accent/50"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5 text-sm font-medium text-fg">
          {title}
          <ArrowRight className="h-3.5 w-3.5 -translate-x-1 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
        </span>
        <span className="mt-0.5 block text-xs leading-relaxed text-muted">
          {description}
        </span>
      </span>
    </Link>
  );
}

function StatusRow({
  label,
  ok,
  detail,
}: {
  label: string;
  ok: boolean;
  detail?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-xs font-medium text-fg">{label}</p>
        {detail && (
          <p className="truncate text-[11px] text-faint" title={detail}>
            {detail}
          </p>
        )}
      </div>
      <Badge tone={ok ? "clean" : "stego"}>
        {ok ? "Online" : "Unavailable"}
      </Badge>
    </div>
  );
}
