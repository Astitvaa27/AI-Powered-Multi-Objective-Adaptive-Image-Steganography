import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BarChart3,
  Cpu,
  FileText,
  Image as ImageIcon,
  ListTree,
  Play,
  Radar,
  ScanSearch,
  Timer,
} from "lucide-react";
import { ApiError } from "@/api/client";
import { analyzeImage, getActiveModel } from "@/api/steganalysis";
import type { AnalysisResult, ImageRecord, ModelInfo } from "@/api/types";
import { AppLayout } from "@/components/layout/AppLayout";
import { ImagePreview } from "@/components/ImagePreview";
import { ImageSelector } from "@/components/ImageSelector";
import { MetricCard } from "@/components/MetricCard";
import {
  DetectionResult,
  FeatureAnalysis,
  ProbabilityChart,
  SuspiciousRegionPanel,
} from "@/components/AnalysisResultViews";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/context/ToastContext";
import { cn } from "@/lib/cn";
import { formatMs, shortId } from "@/lib/format";

const PIPELINE_STEPS = [
  "Reading image data",
  "Extracting statistical features",
  "Running Random Forest detection",
  "Ranking candidate regions",
  "Generating analysis report",
];

type Tab = "regions" | "features" | "report";

export function SteganalysisPage() {
  const { notify } = useToast();

  const [image, setImage] = useState<ImageRecord | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [running, setRunning] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("regions");
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);
  const [showOverlay, setShowOverlay] = useState(true);

  useEffect(() => {
    getActiveModel()
      .then(setModel)
      .catch(() => setModel(null));
  }, []);

  // Advance the visible pipeline stages while the request is in flight.
  useEffect(() => {
    if (!running) return;

    setStepIndex(0);
    const timer = window.setInterval(() => {
      setStepIndex((current) =>
        current < PIPELINE_STEPS.length - 1 ? current + 1 : current,
      );
    }, 700);

    return () => window.clearInterval(timer);
  }, [running]);

  const handleSelect = (selected: ImageRecord) => {
    setImage(selected);
    setResult(null);
    setError(null);
  };

  const runAnalysis = async () => {
    if (!image) return;

    setRunning(true);
    setError(null);
    setResult(null);

    try {
      const analysis = await analyzeImage(image.id);
      setResult(analysis);
      setTab("regions");
      notify(
        `Analysis complete — classified as ${analysis.predicted_class}.`,
        analysis.predicted_class === "STEGO" ? "error" : "success",
      );
    } catch (exception) {
      const message =
        exception instanceof ApiError
          ? exception.message
          : "Steganalysis failed unexpectedly.";
      setError(message);
      notify(message, "error");
    } finally {
      setRunning(false);
    }
  };

  const regions = result?.suspicious_regions ?? [];

  return (
    <AppLayout
      title="Steganalysis"
      subtitle="Classify an image and rank candidate LSB anomaly regions"
    >
      <div className="grid gap-6 xl:grid-cols-[22rem_minmax(0,1fr)] 2xl:grid-cols-[24rem_minmax(0,1fr)]">
        {/* Left rail: input + controls */}
        <div className="space-y-6">
          <Card className="flex max-h-[38rem] flex-col overflow-hidden">
            <CardHeader
              title="Suspect image"
              description="Upload or select the image to analyse"
              icon={<ImageIcon className="h-4 w-4" />}
            />
            <ImageSelector
              selectedId={image?.id ?? null}
              onSelect={handleSelect}
              imageType="SUSPECT"
              allowPathRegistration
              className="min-h-0 flex-1"
            />
          </Card>

          <Card>
            <CardHeader
              title="Detection model"
              icon={<Cpu className="h-4 w-4" />}
              actions={
                model ? (
                  <Badge tone="clean">Active</Badge>
                ) : (
                  <Badge tone="stego">Unavailable</Badge>
                )
              }
            />
            <CardBody className="space-y-3">
              {model ? (
                <dl className="space-y-2 text-xs">
                  <Row label="Name" value={model.name} />
                  <Row label="Version" value={model.version} />
                  <Row label="Architecture" value={model.architecture ?? "—"} />
                  <Row label="Framework" value={model.framework ?? "—"} />
                </dl>
              ) : (
                <p className="text-xs text-muted">
                  No active steganalysis model is registered. Analyses will fail
                  until one is available.
                </p>
              )}

              <Button
                className="w-full"
                size="lg"
                disabled={!image || !model}
                loading={running}
                onClick={() => void runAnalysis()}
              >
                <Play className="h-4 w-4" />
                {running ? "Analysing…" : "Run steganalysis"}
              </Button>

              {!image && (
                <p className="text-center text-[11px] text-faint">
                  Select an image to enable analysis.
                </p>
              )}
            </CardBody>
          </Card>
        </div>

        {/* Right: preview + results */}
        <div className="min-w-0 space-y-6">
          <Card>
            <CardHeader
              title="Image preview"
              description={
                regions.length > 0
                  ? `${regions.length} candidate regions overlaid`
                  : "Zoom and inspect before running detection"
              }
              icon={<ScanSearch className="h-4 w-4" />}
              actions={
                regions.length > 0 && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setShowOverlay((value) => !value)}
                  >
                    {showOverlay ? "Hide overlay" : "Show overlay"}
                  </Button>
                )
              }
            />
            <CardBody>
              <ImagePreview
                imageId={image?.id ?? null}
                meta={image}
                regions={regions}
                naturalWidth={image?.width}
                naturalHeight={image?.height}
                showRegions={showOverlay}
                highlightedRegionId={hoveredRegion}
                onRegionHover={setHoveredRegion}
              />
            </CardBody>
          </Card>

          {running && (
            <Card>
              <LoadingState
                label="Analysing image…"
                steps={PIPELINE_STEPS}
                activeStep={stepIndex}
              />
            </Card>
          )}

          {error && !running && (
            <Card>
              <ErrorState
                title="Analysis failed"
                message={error}
                onRetry={() => void runAnalysis()}
              />
            </Card>
          )}

          {!running && !error && !result && (
            <Card>
              <EmptyState
                icon={<Radar className="h-5 w-5" />}
                title="No result yet"
                description="Select an image and run steganalysis. Results, the feature vector and candidate regions will appear here."
              />
            </Card>
          )}

          {result && !running && (
            <>
              <DetectionResult
                predictedClass={result.predicted_class}
                confidence={result.confidence}
                probabilities={result.probabilities}
              />

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Processing time"
                  value={formatMs(result.processing_time_ms)}
                  icon={<Timer className="h-4 w-4" />}
                />
                <MetricCard
                  label="Features used"
                  value={result.feature_count}
                  hint="Production feature set"
                  icon={<ListTree className="h-4 w-4" />}
                />
                <MetricCard
                  label="Candidate regions"
                  value={regions.length}
                  hint="Anomaly-ranked, not confirmed"
                  icon={<ScanSearch className="h-4 w-4" />}
                />
                <MetricCard
                  label="Session"
                  value={
                    <span className="text-base">
                      {shortId(result.analysis_session_id)}
                    </span>
                  }
                  hint={
                    <Link
                      to={`/reports/${result.analysis_session_id}`}
                      className="text-accent hover:underline"
                    >
                      Open full report
                    </Link>
                  }
                  icon={<FileText className="h-4 w-4" />}
                />
              </div>

              <Card>
                <div className="flex gap-1 border-b border-line px-3 pt-3" role="tablist">
                  {(
                    [
                      { id: "regions", label: "Candidate regions", icon: ScanSearch },
                      { id: "features", label: "Feature analysis", icon: ListTree },
                      { id: "report", label: "Report", icon: FileText },
                    ] as const
                  ).map(({ id, label, icon: Icon }) => (
                    <button
                      key={id}
                      type="button"
                      role="tab"
                      aria-selected={tab === id}
                      onClick={() => setTab(id)}
                      className={cn(
                        "flex items-center gap-1.5 rounded-t-lg px-4 py-2.5 text-xs font-medium transition-colors",
                        tab === id
                          ? "border-b-2 border-accent bg-elevated/50 text-accent"
                          : "border-b-2 border-transparent text-muted hover:text-fg",
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {label}
                    </button>
                  ))}
                </div>

                {tab === "regions" && (
                  <SuspiciousRegionPanel
                    regions={regions}
                    highlightedRegionId={hoveredRegion}
                    onRegionHover={setHoveredRegion}
                  />
                )}

                {tab === "features" && (
                  <FeatureAnalysis features={result.features} />
                )}

                {tab === "report" && (
                  <CardBody className="space-y-5">
                    <div>
                      <h3 className="text-sm font-medium text-fg">
                        {result.analysis_report.title ?? "Analysis report"}
                      </h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted">
                        {result.analysis_report.summary ??
                          "No summary was generated."}
                      </p>
                    </div>

                    <div>
                      <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted">
                        <BarChart3 className="h-3.5 w-3.5" />
                        Class probability distribution
                      </p>
                      <ProbabilityChart probabilities={result.probabilities} />
                    </div>

                    <details className="rounded-lg border border-line bg-elevated/40">
                      <summary className="cursor-pointer px-4 py-2.5 text-xs font-medium text-muted">
                        Raw report data
                      </summary>
                      <pre className="overflow-x-auto border-t border-line px-4 py-3 font-mono text-[11px] leading-relaxed text-muted">
                        {JSON.stringify(result.analysis_report.report_data, null, 2)}
                      </pre>
                    </details>
                  </CardBody>
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-faint">{label}</dt>
      <dd className="truncate text-right font-medium text-fg" title={value}>
        {value}
      </dd>
    </div>
  );
}
