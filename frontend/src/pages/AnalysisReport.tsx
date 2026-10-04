import { useState } from "react";
import { useParams } from "react-router-dom";
import { Cpu, FileText, ImageIcon, ListTree, ScanSearch } from "lucide-react";
import { getSession } from "@/api/steganalysis";
import { useAsync } from "@/hooks/useAsync";
import { formatBytes, formatDateTime, formatMs } from "@/lib/format";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnalysisVerdict, FeatureAnalysis, RegionList } from "@/components/analysis/AnalysisViews";
import { ImagePreview } from "@/components/images/ImagePreview";
import { Badge, statusLabel, statusTone } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Collapsible } from "@/components/ui/Collapsible";
import { ErrorState, LoadingState } from "@/components/ui/States";

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <dt className="shrink-0 text-muted">{label}</dt>
      <dd className={mono ? "truncate text-right font-mono text-xs text-fg" : "truncate text-right text-fg"} title={value}>
        {value}
      </dd>
    </div>
  );
}

export function AnalysisReportPage() {
  const { sessionId = "" } = useParams<{ sessionId: string }>();
  const [hovered, setHovered] = useState<string | null>(null);
  const [showAreas, setShowAreas] = useState(true);

  const { data: detail, loading, error, reload } = useAsync(
    () => getSession(sessionId),
    [sessionId],
    "Couldn't load this report.",
  );

  const back = { to: "/history?tab=analyses", label: "History" };
  const prediction = detail?.prediction ?? null;
  const regions = detail?.suspicious_regions ?? [];

  return (
    <AppLayout
      title="Analysis report"
      description={detail?.image?.original_filename ?? undefined}
      back={back}
      actions={
        detail?.image && (
          <ButtonLink to={`/analyze?image=${detail.image.id}`} variant="secondary" size="sm">
            <ScanSearch className="h-4 w-4" aria-hidden />
            Analyze again
          </ButtonLink>
        )
      }
    >
      {loading && !detail && (
        <Card>
          <LoadingState label="Loading report…" />
        </Card>
      )}

      {error && (
        <Card>
          <ErrorState title="Report unavailable" message={error} onRetry={() => void reload()} />
        </Card>
      )}

      {detail && (
        <div className="space-y-6">
          {detail.status === "FAILED" && (
            <Callout tone="danger" title="This analysis failed">
              {detail.error_message ?? "No error message was recorded."}
            </Callout>
          )}

          {prediction && (
            <AnalysisVerdict predictedClass={prediction.predicted_class} probabilities={prediction.probabilities} />
          )}

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
            <Card>
              <CardHeader
                icon={<ImageIcon className="h-4 w-4" />}
                title="Analyzed image"
                description={regions.length ? `${regions.length} unusual areas marked` : undefined}
                actions={
                  regions.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setShowAreas((value) => !value)}
                      className="text-sm font-medium text-accent hover:underline"
                    >
                      {showAreas ? "Hide markers" : "Show markers"}
                    </button>
                  )
                }
              />
              <CardBody>
                <ImagePreview
                  imageId={detail.image?.id ?? null}
                  alt={detail.image?.original_filename}
                  width={detail.image?.width}
                  height={detail.image?.height}
                  regions={regions}
                  showRegions={showAreas}
                  highlightedRegionId={hovered}
                  onRegionHover={setHovered}
                  emptyText="The image for this report is no longer available."
                />
              </CardBody>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader
                  icon={<FileText className="h-4 w-4" />}
                  title="Details"
                  actions={<Badge tone={statusTone(detail.status)}>{statusLabel(detail.status)}</Badge>}
                />
                <CardBody>
                  <dl className="divide-y divide-line text-sm">
                    <Row label="Analyzed" value={formatDateTime(detail.created_at)} />
                    <Row label="Processing time" value={formatMs(detail.processing_time_ms)} />
                    <Row label="Measurements used" value={String(detail.feature_count ?? "—")} />
                    {detail.image && (
                      <>
                        <Row label="Dimensions" value={`${detail.image.width} × ${detail.image.height} px`} />
                        <Row label="File size" value={formatBytes(detail.image.file_size_bytes)} />
                      </>
                    )}
                    <Row label="Report ID" value={detail.analysis_session_id} mono />
                  </dl>
                </CardBody>
              </Card>

              {detail.model && (
                <Card>
                  <CardHeader icon={<Cpu className="h-4 w-4" />} title="Detector" />
                  <CardBody>
                    <dl className="divide-y divide-line text-sm">
                      <Row label="Name" value={detail.model.name} />
                      <Row label="Version" value={detail.model.version} />
                      <Row label="Type" value={detail.model.architecture ?? "—"} />
                      <Row label="Framework" value={detail.model.framework ?? "—"} />
                    </dl>
                  </CardBody>
                </Card>
              )}
            </div>
          </div>

          <Card>
            <CardHeader
              icon={<ScanSearch className="h-4 w-4" />}
              title="Unusual areas"
              description="Blocks ranked by how unusual their pixel bits are"
            />
            <RegionList regions={regions} highlightedRegionId={hovered} onRegionHover={setHovered} />
          </Card>

          <Card>
            <CardHeader icon={<ListTree className="h-4 w-4" />} title="Detector inputs" />
            <FeatureAnalysis features={detail.features} />
          </Card>

          {detail.report && (
            <Card>
              <CardHeader
                icon={<FileText className="h-4 w-4" />}
                title={detail.report.title ?? "Saved report"}
                description={detail.report.summary ?? undefined}
              />
              <Collapsible title="Raw report data" description="The exact data stored by the server">
                <pre className="max-h-96 overflow-auto rounded-lg border border-line bg-elevated/50 p-4 font-mono text-xs leading-relaxed text-muted">
                  {JSON.stringify(detail.report.report_data, null, 2)}
                </pre>
              </Collapsible>
            </Card>
          )}
        </div>
      )}
    </AppLayout>
  );
}
