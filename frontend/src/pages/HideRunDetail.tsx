import { useState } from "react";
import { useParams } from "react-router-dom";
import { Download, KeyRound, ScanSearch } from "lucide-react";
import { getImage, downloadImage } from "@/api/images";
import { getAdaptiveRun } from "@/api/steganography";
import { useToast } from "@/context/ToastContext";
import { errorMessage, useAsync } from "@/hooks/useAsync";
import { methodWithParams } from "@/lib/describe";
import { formatDateTime, shortId } from "@/lib/format";
import { AppLayout } from "@/components/layout/AppLayout";
import { DetectionSummary, SelectionDetails } from "@/components/hide/SelectionDetails";
import { VisualComparison } from "@/components/hide/VisualComparison";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorState, LoadingState } from "@/components/ui/States";

/** Re-opens a stored automatic run with its full candidate comparison. */
export function HideRunDetailPage() {
  const { runId = "" } = useParams<{ runId: string }>();
  const { notify } = useToast();
  const [downloading, setDownloading] = useState(false);

  const { data, loading, error, reload } = useAsync(
    async () => {
      const run = await getAdaptiveRun(runId);
      // The original may have been removed; the comparison still renders.
      const cover = await getImage(run.cover_image_id).catch(() => null);
      return { run, cover };
    },
    [runId],
    "Couldn't load this run.",
  );

  const run = data?.run;
  const cover = data?.cover;
  const method = run
    ? methodWithParams(run.selected_method, run.selected_parameters?.channel_mode, run.selected_parameters?.lsb_bits)
    : "";

  const download = async () => {
    if (!run?.stego_image_id) return;
    setDownloading(true);
    try {
      await downloadImage(run.stego_image_id, `stegolab_${(run.selected_method ?? "image").toLowerCase()}_${shortId(run.optimization_run_id)}.png`);
    } catch (exception) {
      notify(errorMessage(exception, "The download failed."), "error");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <AppLayout
      title="Hidden message details"
      description={run ? `${formatDateTime(run.created_at)} · chosen method: ${method}` : undefined}
      back={{ to: "/history", label: "History" }}
      actions={
        run?.stego_image_id && (
          <>
            <Button size="sm" onClick={() => void download()} loading={downloading}>
              <Download className="h-4 w-4" aria-hidden />
              Download image
            </Button>
            <ButtonLink to={`/extract?image=${run.stego_image_id}`} variant="secondary" size="sm">
              <KeyRound className="h-4 w-4" aria-hidden />
              Extract
            </ButtonLink>
            <ButtonLink to={`/analyze?image=${run.stego_image_id}`} variant="secondary" size="sm">
              <ScanSearch className="h-4 w-4" aria-hidden />
              Analyze
            </ButtonLink>
          </>
        )
      }
    >
      {loading && !data && (
        <Card>
          <LoadingState label="Loading run…" />
        </Card>
      )}
      {error && (
        <Card>
          <ErrorState title="Run unavailable" message={error} onRetry={() => void reload()} />
        </Card>
      )}

      {run && (
        <div className="space-y-6">
          {cover && run.stego_image_id && (
            <VisualComparison
              coverId={cover.id}
              stegoId={run.stego_image_id}
              width={cover.width}
              height={cover.height}
              coverFormat={cover.mime_type || cover.file_extension}
            />
          )}
          <SelectionDetails comparison={run} />
          {run.steganalysis && <DetectionSummary steganalysis={run.steganalysis} />}
        </div>
      )}
    </AppLayout>
  );
}
