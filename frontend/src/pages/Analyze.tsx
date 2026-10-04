import { useEffect, useState } from "react";
import { FileText, ScanSearch } from "lucide-react";
import { analyzeImage, getActiveModel } from "@/api/steganalysis";
import type { AnalysisResult, ImageRecord, ModelInfo } from "@/api/types";
import { errorMessage } from "@/hooks/useAsync";
import { useImageFromQuery } from "@/hooks/useImageFromQuery";
import { formatMs } from "@/lib/format";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnalysisVerdict, FeatureAnalysis, RegionList } from "@/components/analysis/AnalysisViews";
import { ImagePicker } from "@/components/images/ImagePicker";
import { ImagePreview } from "@/components/images/ImagePreview";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { WorkingState } from "@/components/ui/States";

const STAGES = [
  "Measuring pixel-bit statistics across the image",
  "Running the detector on those measurements",
  "Scanning blocks of the image for unusual areas",
  "Saving the report to your history",
];

type ResultTab = "areas" | "inputs";

export function AnalyzePage() {
  const [image, setImage] = useState<ImageRecord | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [tab, setTab] = useState<ResultTab>("areas");
  const [showAreas, setShowAreas] = useState(true);
  const [hovered, setHovered] = useState<string | null>(null);

  const loadingImage = useImageFromQuery(setImage);

  useEffect(() => {
    getActiveModel()
      .then(setModel)
      .catch((exception) =>
        setModelError(errorMessage(exception, "The detector is unavailable.")),
      );
  }, []);

  const selectImage = (next: ImageRecord | null) => {
    setImage(next);
    setResult(null);
    setError(null);
    setImageError(null);
  };

  const submit = async () => {
    if (running) return;
    if (!image) {
      setImageError("Choose the image you want to check.");
      return;
    }

    setRunning(true);
    setError(null);
    setResult(null);

    try {
      setResult(await analyzeImage(image.id));
      setTab("areas");
    } catch (exception) {
      setError(errorMessage(exception, "The analysis failed unexpectedly."));
    } finally {
      setRunning(false);
    }
  };

  const regions = result?.suspicious_regions ?? [];

  return (
    <AppLayout
      title="Analyze an Image"
      description="Estimate whether an image is likely to contain hidden data."
    >
      {modelError && (
        <Callout tone="warning" title="Analysis is unavailable right now" className="mb-4">
          The server reported: “{modelError}” Hiding and extracting messages still work.
        </Callout>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card className="p-5 sm:p-6">
            <h2 className="text-base font-semibold text-fg">Choose an image</h2>
            <p className="mt-0.5 text-sm text-muted">Any image — yours, downloaded, or from your library.</p>
            <div className="mt-4">
              {loadingImage ? (
                <p className="text-sm text-muted">Loading image…</p>
              ) : (
                <ImagePicker value={image} onChange={selectImage} uploadAs="SUSPECT" allowPathRegistration />
              )}
              {imageError && <p className="mt-2 text-xs text-stego" role="alert">{imageError}</p>}
            </div>

            {!running && (
              <Button
                size="lg"
                className="mt-5 w-full"
                onClick={() => void submit()}
                disabled={Boolean(modelError)}
              >
                <ScanSearch className="h-4 w-4" aria-hidden />
                Analyze image
              </Button>
            )}
            {model && (
              <p className="mt-3 text-xs text-muted">
                Detector: {model.name} {model.version}
                {model.architecture ? ` · ${model.architecture}` : ""}
              </p>
            )}
          </Card>

          {running && (
            <Card>
              <WorkingState
                title="Analyzing the image…"
                description="Usually a few seconds; larger images take longer."
                stages={STAGES}
              />
            </Card>
          )}

          {error && !running && (
            <Callout tone="danger" role="alert" title="The analysis didn't complete">
              {error}
            </Callout>
          )}
        </div>

        <div className="min-w-0 space-y-6">
          {result && !running && (
            <AnalysisVerdict predictedClass={result.predicted_class} probabilities={result.probabilities} />
          )}

          <Card>
            <CardHeader
              title={result ? "Image with unusual areas marked" : "Preview"}
              description={
                result
                  ? `${regions.length} area${regions.length === 1 ? "" : "s"} flagged · analyzed in ${formatMs(result.processing_time_ms)}`
                  : "Zoom in to inspect the image before analyzing."
              }
              actions={
                regions.length > 0 && (
                  <Button variant="secondary" size="sm" onClick={() => setShowAreas((value) => !value)}>
                    {showAreas ? "Hide markers" : "Show markers"}
                  </Button>
                )
              }
            />
            <CardBody>
              <ImagePreview
                imageId={image?.id ?? null}
                alt={image?.original_filename}
                width={image?.width}
                height={image?.height}
                regions={regions}
                showRegions={showAreas}
                highlightedRegionId={hovered}
                onRegionHover={setHovered}
                emptyText="Upload or choose an image on the left."
              />
            </CardBody>
          </Card>

          {result && !running && (
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-3 pr-5">
                <Tabs
                  label="Analysis details"
                  value={tab}
                  onChange={setTab}
                  className="flex-1 border-b-0 px-5"
                  options={[
                    { value: "areas", label: "Unusual areas" },
                    { value: "inputs", label: "Detector inputs" },
                  ]}
                />
                <ButtonLink
                  to={`/history/analyses/${result.analysis_session_id}`}
                  variant="secondary"
                  size="sm"
                >
                  <FileText className="h-3.5 w-3.5" aria-hidden />
                  Full report
                </ButtonLink>
              </div>
              <div className="border-t border-line">
                {tab === "areas" ? (
                  <RegionList regions={regions} highlightedRegionId={hovered} onRegionHover={setHovered} />
                ) : (
                  <FeatureAnalysis features={result.features} />
                )}
              </div>
            </Card>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
