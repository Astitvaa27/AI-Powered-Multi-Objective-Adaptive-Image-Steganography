import { Link } from "react-router-dom";
import { ArrowRight, KeyRound, LockKeyhole, ScanSearch } from "lucide-react";
import { getActiveModel, getStats, listSessions } from "@/api/steganalysis";
import { listSteganographySessions } from "@/api/steganography";
import type { AnalysisSessionSummary, SteganographySessionSummary } from "@/api/types";
import { useAuth } from "@/context/AuthContext";
import { useAsync } from "@/hooks/useAsync";
import { methodName } from "@/lib/describe";
import { formatNumber, formatPercent, formatRelative } from "@/lib/format";
import { AppLayout } from "@/components/layout/AppLayout";
import { Badge, statusLabel, statusTone } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card, CardHeader } from "@/components/ui/Card";
import { Stat } from "@/components/ui/Stat";
import { ErrorState, SkeletonRows } from "@/components/ui/States";

const TOOLS = [
  {
    to: "/hide",
    icon: LockKeyhole,
    title: "Hide a message",
    text: "Conceal text inside an image. StegoLab picks the least noticeable way to do it.",
  },
  {
    to: "/extract",
    icon: KeyRound,
    title: "Extract a message",
    text: "Read the hidden text back from an image you created.",
  },
  {
    to: "/analyze",
    icon: ScanSearch,
    title: "Analyze an image",
    text: "Estimate whether any image is likely to contain hidden data.",
  },
];

function ToolCard({ to, icon: Icon, title, text }: (typeof TOOLS)[number]) {
  return (
    <Link
      to={to}
      className="group panel flex flex-col p-5 transition-colors hover:border-accent/40 hover:bg-accent-soft/30"
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-soft text-accent">
        <Icon className="h-5 w-5" aria-hidden />
      </span>
      <span className="mt-4 flex items-center gap-1.5 text-base font-semibold text-fg">
        {title}
        <ArrowRight
          className="h-4 w-4 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
          aria-hidden
        />
      </span>
      <span className="mt-1 text-sm leading-relaxed text-muted">{text}</span>
    </Link>
  );
}

function GettingStarted() {
  const steps = [
    { title: "Hide a message", text: "Upload a photo, type a message, and let StegoLab choose how to hide it." },
    { title: "Download and share", text: "Save the new PNG. It looks the same, but carries your text." },
    { title: "Extract or analyze", text: "Read the message back, or check how detectable it is." },
  ];

  return (
    <Card className="p-6">
      <h2 className="text-base font-semibold text-fg">New here? Start in three steps</h2>
      <ol className="mt-5 grid gap-5 md:grid-cols-3">
        {steps.map((step, index) => (
          <li key={step.title} className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent">
              {index + 1}
            </span>
            <span>
              <span className="block text-sm font-medium text-fg">{step.title}</span>
              <span className="mt-0.5 block text-sm leading-relaxed text-muted">{step.text}</span>
            </span>
          </li>
        ))}
      </ol>
      <ButtonLink to="/hide" className="mt-6">
        Hide your first message
        <ArrowRight className="h-4 w-4" aria-hidden />
      </ButtonLink>
    </Card>
  );
}

function RecentHidden({ items }: { items: SteganographySessionSummary[] }) {
  if (items.length === 0) {
    return <p className="px-5 py-6 text-sm text-muted">Nothing hidden yet.</p>;
  }
  return (
    <ul className="divide-y divide-line">
      {items.map((session) => (
        <li key={session.id}>
          <Link
            to={session.optimization_run_id ? `/history/hides/${session.optimization_run_id}` : "/history"}
            className="flex items-center gap-3 px-5 py-3 hover:bg-elevated/50"
          >
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-fg">
                {session.cover_image_filename ?? "Image"}
              </span>
              <span className="block text-xs text-muted">
                {session.method ? methodName(session.method) : "—"}
                {session.psnr !== null && ` · ${formatNumber(session.psnr, 1)} dB`} ·{" "}
                {formatRelative(session.created_at)}
              </span>
            </span>
            <Badge tone={statusTone(session.status)}>{statusLabel(session.status)}</Badge>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function RecentAnalyses({ items }: { items: AnalysisSessionSummary[] }) {
  if (items.length === 0) {
    return <p className="px-5 py-6 text-sm text-muted">No images analyzed yet.</p>;
  }
  return (
    <ul className="divide-y divide-line">
      {items.map((session) => (
        <li key={session.analysis_session_id}>
          <Link
            to={`/history/analyses/${session.analysis_session_id}`}
            className="flex items-center gap-3 px-5 py-3 hover:bg-elevated/50"
          >
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-fg">
                {session.image_filename ?? "Unnamed image"}
              </span>
              <span className="block text-xs text-muted">
                hidden-data probability {formatPercent(session.probabilities?.STEGO ?? null, 0)} ·{" "}
                {formatRelative(session.created_at)}
              </span>
            </span>
            {session.predicted_class ? (
              <Badge tone={session.predicted_class === "STEGO" ? "stego" : "clean"}>
                {session.predicted_class === "STEGO" ? "Likely hidden" : "Nothing found"}
              </Badge>
            ) : (
              <Badge tone={statusTone(session.status)}>{statusLabel(session.status)}</Badge>
            )}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function DashboardPage() {
  const { profile } = useAuth();

  const { data, loading, error, reload } = useAsync(
    async () => {
      // Each panel degrades independently; one failing call doesn't blank the page.
      const [stats, analyses, hidden, model] = await Promise.allSettled([
        getStats(),
        listSessions({ limit: 5 }),
        listSteganographySessions({ limit: 5 }),
        getActiveModel(),
      ]);

      if (hidden.status === "rejected" && analyses.status === "rejected") {
        throw hidden.reason;
      }

      return {
        stats: stats.status === "fulfilled" ? stats.value : null,
        analyses: analyses.status === "fulfilled" ? analyses.value : null,
        hidden: hidden.status === "fulfilled" ? hidden.value : null,
        modelAvailable: model.status === "fulfilled",
      };
    },
    [],
    "Couldn't load your activity.",
  );

  const hiddenTotal = data?.hidden?.total ?? 0;
  const analysesTotal = data?.analyses?.total ?? 0;
  const isNew = Boolean(data?.hidden && data?.analyses) && hiddenTotal === 0 && analysesTotal === 0;
  const name = profile?.email?.split("@")[0];

  return (
    <AppLayout
      title={name ? `Welcome back, ${name}` : "Welcome to StegoLab"}
      pageTitle="Dashboard"
      description="What would you like to do?"
    >
      <div className="space-y-8">
        <div className="grid gap-4 md:grid-cols-3">
          {TOOLS.map((tool) => (
            <ToolCard key={tool.to} {...tool} />
          ))}
        </div>

        {data && !data.modelAvailable && (
          <Callout tone="warning" title="Image analysis is currently unavailable">
            No active detection model is registered on the server. Hiding and
            extracting messages still work.
          </Callout>
        )}

        {loading && !data && (
          <Card>
            <SkeletonRows rows={4} />
          </Card>
        )}

        {error && (
          <Card>
            <ErrorState message={error} onRetry={() => void reload()} />
          </Card>
        )}

        {isNew && <GettingStarted />}

        {data && !isNew && (
          <>
            <section aria-labelledby="overview-heading">
              <h2 id="overview-heading" className="mb-3 text-base font-semibold text-fg">
                Your activity
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Stat label="Messages hidden" value={hiddenTotal} />
                <Stat label="Images analyzed" value={analysesTotal} />
                {data.stats && (
                  <>
                    <Stat
                      label="Flagged as likely hidden"
                      value={data.stats.stego_count}
                      hint={
                        data.stats.stego_count + data.stats.clean_count > 0
                          ? `${formatPercent(
                              data.stats.stego_count / (data.stats.stego_count + data.stats.clean_count),
                              0,
                            )} of analyses`
                          : undefined
                      }
                    />
                    <Stat label="Images in your library" value={data.stats.total_images} />
                  </>
                )}
              </div>
            </section>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader
                  title="Recently hidden"
                  actions={
                    <ButtonLink to="/history" variant="ghost" size="sm">
                      View all
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                    </ButtonLink>
                  }
                />
                <RecentHidden items={data.hidden?.items ?? []} />
              </Card>
              <Card>
                <CardHeader
                  title="Recently analyzed"
                  actions={
                    <ButtonLink to="/history?tab=analyses" variant="ghost" size="sm">
                      View all
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                    </ButtonLink>
                  }
                />
                <RecentAnalyses items={data.analyses?.items ?? []} />
              </Card>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
