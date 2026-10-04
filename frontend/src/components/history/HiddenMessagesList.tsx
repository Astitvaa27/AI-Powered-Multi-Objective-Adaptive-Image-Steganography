import { useState } from "react";
import { Link } from "react-router-dom";
import { Download, KeyRound, LockKeyhole } from "lucide-react";
import { downloadImage } from "@/api/images";
import { listSteganographySessions } from "@/api/steganography";
import type { SteganographySessionSummary } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { errorMessage, useAsync } from "@/hooks/useAsync";
import { methodName } from "@/lib/describe";
import { formatDateTime, formatNumber, shortId } from "@/lib/format";
import { Badge, statusLabel, statusTone } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";

const PAGE_SIZE = 20;

function MethodCell({ session }: { session: SteganographySessionSummary }) {
  if (!session.method) return <span className="text-muted">—</span>;
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      <span className="text-fg">{methodName(session.method)}</span>
      <Badge tone={session.embedding_mode === "ADAPTIVE" ? "accent" : "neutral"}>
        {session.embedding_mode === "ADAPTIVE" ? "Automatic" : "Manual"}
      </Badge>
    </span>
  );
}

function Actions({ session }: { session: SteganographySessionSummary }) {
  const { notify } = useToast();
  const [downloading, setDownloading] = useState(false);

  if (!session.stego_image_id) return null;
  const stegoId = session.stego_image_id;

  const download = async () => {
    setDownloading(true);
    try {
      await downloadImage(stegoId, `stegolab_${(session.method ?? "image").toLowerCase()}_${shortId(session.id)}.png`);
    } catch (exception) {
      notify(errorMessage(exception, "The download failed."), "error");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {session.optimization_run_id && (
        <ButtonLink to={`/history/hides/${session.optimization_run_id}`} variant="secondary" size="sm">
          Details
        </ButtonLink>
      )}
      <Button
        variant="ghost"
        size="sm"
        loading={downloading}
        onClick={() => void download()}
        aria-label={`Download image from ${formatDateTime(session.created_at)}`}
      >
        {!downloading && <Download className="h-4 w-4" aria-hidden />}
        <span className="hidden xl:inline">Download</span>
      </Button>
      <ButtonLink
        to={`/extract?image=${stegoId}`}
        variant="ghost"
        size="sm"
        aria-label={`Extract the message from the image created ${formatDateTime(session.created_at)}`}
      >
        <KeyRound className="h-4 w-4" aria-hidden />
        <span className="hidden xl:inline">Extract</span>
      </ButtonLink>
    </div>
  );
}

export function HiddenMessagesList() {
  const [page, setPage] = useState(0);
  const { data, loading, error, reload } = useAsync(
    () => listSteganographySessions({ limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    [page],
    "Couldn't load your hidden messages.",
  );

  if (loading && !data) return <SkeletonRows rows={6} />;
  if (error) return <ErrorState message={error} onRetry={() => void reload()} />;
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        icon={<LockKeyhole className="h-5 w-5" />}
        title="No hidden messages yet"
        description="Every message you hide is listed here, with its image ready to download."
        action={<ButtonLink to="/hide">Hide a message</ButtonLink>}
      />
    );
  }

  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs text-muted">
            <tr>
              <th scope="col" className="px-5 py-2.5 font-medium">Date</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Original image</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Method</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Quality</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Status</th>
              <th scope="col" className="px-5 py-2.5 font-medium">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {data.items.map((session) => (
              <tr key={session.id} className="align-middle">
                <td className="whitespace-nowrap px-5 py-3 text-muted">{formatDateTime(session.created_at)}</td>
                <td className="max-w-[14rem] truncate px-3 py-3 text-fg" title={session.cover_image_filename ?? undefined}>
                  {session.cover_image_filename ?? "—"}
                </td>
                <td className="px-3 py-3">
                  <MethodCell session={session} />
                </td>
                <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-fg">
                  {session.psnr !== null ? `${formatNumber(session.psnr, 1)} dB` : session.status === "COMPLETED" ? "∞" : "—"}
                </td>
                <td className="px-3 py-3">
                  <Badge tone={statusTone(session.status)} title={session.error_message ?? undefined}>
                    {statusLabel(session.status)}
                  </Badge>
                </td>
                <td className="px-5 py-3">
                  <Actions session={session} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="divide-y divide-line md:hidden">
        {data.items.map((session) => (
          <li key={session.id} className="space-y-2 px-4 py-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-fg">{session.cover_image_filename ?? "Image"}</p>
                <p className="text-xs text-muted">{formatDateTime(session.created_at)}</p>
              </div>
              <Badge tone={statusTone(session.status)}>{statusLabel(session.status)}</Badge>
            </div>
            <div className="text-sm">
              <MethodCell session={session} />
            </div>
            {session.error_message && <p className="text-xs text-stego">{session.error_message}</p>}
            <Actions session={session} />
          </li>
        ))}
      </ul>

      <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={setPage} />
      <p className="border-t border-line px-5 py-3 text-xs text-muted">
        Details with the full comparison are available for automatic runs.{" "}
        <Link to="/hide" className="font-medium text-accent hover:underline">
          Hide another message
        </Link>
      </p>
    </>
  );
}
