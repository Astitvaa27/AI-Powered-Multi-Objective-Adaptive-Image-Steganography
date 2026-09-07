import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  Cpu,
  FileText,
  ListTree,
  ScanSearch,
  Timer,
} from "lucide-react";
import { ApiError } from "@/api/client";
import { getSession } from "@/api/steganalysis";
import type { AnalysisSessionDetail } from "@/api/types";
import { AppLayout } from "@/components/layout/AppLayout";
import { ImagePreview } from "@/components/ImagePreview";
import { MetricCard } from "@/components/MetricCard";
import {
  DetectionResult,
  FeatureAnalysis,
  ProbabilityChart,
  SuspiciousRegionPanel,
} from "@/components/AnalysisResultViews";
import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatBytes, formatDateTime, formatMs } from "@/lib/format";

export function ReportDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const [detail, setDetail] = useState<AnalysisSessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      setDetail(await getSession(sessionId));
    } catch (exception) {
      setError(
        exception instanceof ApiError
          ? exception.message
          : "Unable to load this analysis report.",
      );
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const prediction = detail?.prediction ?? null;
  const regions = detail?.suspicious_regions ?? [];

  return (
    <AppLayout
      title="Analysis report"
      subtitle={detail?.image?.original_filename ?? sessionId}
    >
      <div className="mb-5">
        <Link to="/reports">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to reports
          </Button>
        </Link>
      </div>

      {loading && (
        <Card>
          <LoadingState label="Loading report…" />
        </Card>
      )}

      {!loading && error && (
        <Card>
          <ErrorState message={error} onRetry={() => void load()} />
        </Card>
      )}

      {!loading && !error && detail && (
        <div className="space-y-6">
          {detail.status === "FAILED" && (
            <Card>
              <ErrorState
                title="This analysis failed"
                message={
                  detail.error_message ??
                  "The backend did not record an error message for this session."
                }
              />
            </Card>
          )}

          {prediction && (
            <DetectionResult
              predictedClass={prediction.predicted_class}
              confidence={prediction.confidence}
              probabilities={prediction.probabilities}
            />
          )}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Processing time"
              value={formatMs(detail.processing_time_ms)}
              icon={<Timer className="h-4 w-4" />}
            />
            <MetricCard
              label="Features"
              value={detail.feature_count ?? "—"}
              icon={<ListTree className="h-4 w-4" />}
            />
            <MetricCard
              label="Candidate regions"
              value={regions.length}
              hint="Anomaly-ranked, not confirmed"
              icon={<ScanSearch className="h-4 w-4" />}
            />
            <MetricCard
              label="Analysed"
              value={
                <span className="text-base">
                  {formatDateTime(detail.created_at)}
                </span>
              }
              hint={detail.analysis_type}
              icon={<FileText className="h-4 w-4" />}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
            <Card>
              <CardHeader
                title="Analysed image"
                description={
                  regions.length > 0
                    ? `${regions.length} candidate regions overlaid`
                    : undefined
                }
                icon={<ScanSearch className="h-4 w-4" />}
              />
              <CardBody>
                <ImagePreview
                  imageId={detail.image?.id ?? null}
                  meta={
                    detail.image
                      ? {
                          original_filename: detail.image.original_filename,
                          width: detail.image.width,
                          height: detail.image.height,
                          channels: detail.image.channels,
                          file_size_bytes: detail.image.file_size_bytes,
                          file_extension: detail.image.file_extension,
                        }
                      : null
                  }
                  regions={regions}
                  naturalWidth={detail.image?.width}
                  naturalHeight={detail.image?.height}
                  highlightedRegionId={hoveredRegion}
                  onRegionHover={setHoveredRegion}
                />
              </CardBody>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader
                  title="Session details"
                  icon={<FileText className="h-4 w-4" />}
                  actions={
                    <Badge tone={statusTone(detail.status)}>
                      {detail.status}
                    </Badge>
                  }
                />
                <CardBody>
                  <dl className="space-y-2.5 text-xs">
                    <DetailRow
                      label="Session ID"
                      value={detail.analysis_session_id}
                      mono
                    />
                    <DetailRow
                      label="Started"
                      value={formatDateTime(detail.started_at)}
                    />
                    <DetailRow
                      label="Completed"
                      value={formatDateTime(detail.completed_at)}
                    />
                    {detail.image && (
                      <>
                        <DetailRow
                          label="Dimensions"
                          value={`${detail.image.width} × ${detail.image.height}`}
                        />
                        <DetailRow
                          label="Channels"
                          value={String(detail.image.channels)}
                        />
                        <DetailRow
                          label="File size"
                          value={formatBytes(detail.image.file_size_bytes)}
                        />
                        <DetailRow
                          label="Storage path"
                          value={detail.image.storage_path}
                          mono
                        />
                      </>
                    )}
                  </dl>
                </CardBody>
              </Card>

              {detail.model && (
                <Card>
                  <CardHeader
                    title="Model"
                    icon={<Cpu className="h-4 w-4" />}
                  />
                  <CardBody>
                    <dl className="space-y-2.5 text-xs">
                      <DetailRow label="Name" value={detail.model.name} />
                      <DetailRow label="Version" value={detail.model.version} />
                      <DetailRow
                        label="Architecture"
                        value={detail.model.architecture ?? "—"}
                      />
                      <DetailRow
                        label="Framework"
                        value={detail.model.framework ?? "—"}
                      />
                    </dl>
                  </CardBody>
                </Card>
              )}

              {prediction && (
                <Card>
                  <CardHeader
                    title="Class probabilities"
                    icon={<BarChart3 className="h-4 w-4" />}
                  />
                  <CardBody>
                    <ProbabilityChart probabilities={prediction.probabilities} />
                  </CardBody>
                </Card>
              )}
            </div>
          </div>

          <Card>
            <CardHeader
              title="Candidate suspicious regions"
              description="Ranked by local LSB anomaly score"
              icon={<ScanSearch className="h-4 w-4" />}
            />
            <SuspiciousRegionPanel
              regions={regions}
              highlightedRegionId={hoveredRegion}
              onRegionHover={setHoveredRegion}
            />
          </Card>

          <Card>
            <CardHeader
              title="Feature analysis"
              description="Values supplied to the classifier for this image"
              icon={<ListTree className="h-4 w-4" />}
            />
            <FeatureAnalysis features={detail.features} />
          </Card>

          {detail.report && (
            <Card>
              <CardHeader
                title={detail.report.title ?? "Report"}
                description={detail.report.summary ?? undefined}
                icon={<FileText className="h-4 w-4" />}
                actions={
                  <Badge tone={statusTone(detail.report.status)}>
                    {detail.report.status}
                  </Badge>
                }
              />
              <CardBody className="space-y-4">
                <dl className="grid gap-2.5 text-xs sm:grid-cols-2">
                  {Object.entries(detail.report.report_data)
                    .filter(([key]) => key !== "features")
                    .map(([key, value]) => (
                      <DetailRow
                        key={key}
                        label={key.replace(/_/g, " ")}
                        value={
                          typeof value === "object" && value !== null
                            ? JSON.stringify(value)
                            : String(value)
                        }
                      />
                    ))}
                </dl>

                <details className="rounded-lg border border-line bg-elevated/40">
                  <summary className="cursor-pointer px-4 py-2.5 text-xs font-medium text-muted">
                    Raw data
                  </summary>
                  <pre className="max-h-96 overflow-auto border-t border-line px-4 py-3 font-mono text-[11px] leading-relaxed text-muted">
                    {JSON.stringify(detail.report.report_data, null, 2)}
                  </pre>
                </details>
              </CardBody>
            </Card>
          )}
        </div>
      )}
    </AppLayout>
  );
}

function DetailRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 capitalize text-faint">{label}</dt>
      <dd
        className={
          mono
            ? "truncate text-right font-mono text-[11px] text-fg"
            : "truncate text-right font-medium text-fg"
        }
        title={value}
      >
        {value}
      </dd>
    </div>
  );
}
