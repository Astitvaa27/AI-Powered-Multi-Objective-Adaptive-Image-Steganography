import { useCallback, useEffect, useState } from "react";
import {
  Cpu,
  Database,
  Info,
  Monitor,
  Moon,
  Server,
  Sun,
} from "lucide-react";
import { checkDatabaseHealth, checkHealth } from "@/api/auth";
import { API_BASE_URL } from "@/api/client";
import { getActiveModel } from "@/api/steganalysis";
import type { ModelInfo } from "@/api/types";
import { AppLayout } from "@/components/layout/AppLayout";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/States";
import { useAuth } from "@/context/AuthContext";
import { useTheme, type Theme } from "@/context/ThemeContext";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";

export function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { userId } = useAuth();

  const [api, setApi] = useState<boolean | null>(null);
  const [database, setDatabase] = useState<boolean | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  const runChecks = useCallback(async () => {
    setChecking(true);

    const [apiResult, dbResult, modelResult] = await Promise.allSettled([
      checkHealth(),
      checkDatabaseHealth(),
      getActiveModel(),
    ]);

    setApi(apiResult.status === "fulfilled");
    setDatabase(dbResult.status === "fulfilled");

    if (modelResult.status === "fulfilled") {
      setModel(modelResult.value);
      setModelError(null);
    } else {
      setModel(null);
      setModelError(
        modelResult.reason instanceof Error
          ? modelResult.reason.message
          : "The active steganalysis model could not be reached.",
      );
    }

    setChecking(false);
  }, []);

  useEffect(() => {
    void runChecks();
  }, [runChecks]);

  const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
  ];

  return (
    <AppLayout title="Settings" subtitle="Appearance, backend and model status">
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader
            title="Appearance"
            description="Your theme preference is stored in this browser and applies to every page."
            icon={<Monitor className="h-4 w-4" />}
          />
          <CardBody>
            <fieldset>
              <legend className="sr-only">Theme</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {themeOptions.map(({ value, label, icon: Icon }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setTheme(value)}
                    aria-pressed={theme === value}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border p-4 text-left transition-colors",
                      theme === value
                        ? "border-accent bg-accent-soft"
                        : "border-line bg-elevated/40 hover:border-faint",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                        theme === value
                          ? "bg-accent text-white dark:text-[rgb(var(--bg))]"
                          : "bg-surface text-muted",
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    <span>
                      <span
                        className={cn(
                          "block text-sm font-medium",
                          theme === value ? "text-accent" : "text-fg",
                        )}
                      >
                        {label} mode
                      </span>
                      <span className="block text-[11px] text-muted">
                        {value === "dark"
                          ? "Low-glare palette for long analysis sessions"
                          : "High-contrast palette for bright rooms"}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </fieldset>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Backend connection"
            description="Configured through the VITE_API_BASE_URL environment variable"
            icon={<Server className="h-4 w-4" />}
            actions={
              <Button
                variant="secondary"
                size="sm"
                loading={checking}
                onClick={() => void runChecks()}
              >
                Re-check
              </Button>
            }
          />
          <CardBody className="space-y-3">
            <div className="rounded-lg border border-line bg-elevated/40 px-3 py-2.5">
              <p className="text-[11px] uppercase tracking-wide text-faint">
                API base URL
              </p>
              <p className="mt-0.5 break-all font-mono text-xs text-fg">
                {API_BASE_URL}
              </p>
            </div>

            <HealthRow
              label="API server"
              icon={<Server className="h-3.5 w-3.5" />}
              state={api}
              checking={checking}
            />
            <HealthRow
              label="Database"
              icon={<Database className="h-3.5 w-3.5" />}
              state={database}
              checking={checking}
            />

            {userId && (
              <div className="rounded-lg border border-line bg-elevated/40 px-3 py-2.5">
                <p className="text-[11px] uppercase tracking-wide text-faint">
                  Signed-in user
                </p>
                <p className="mt-0.5 break-all font-mono text-xs text-fg">
                  {userId}
                </p>
              </div>
            )}
          </CardBody>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader
            title="Steganalysis model"
            description="The active detection model registered in the database"
            icon={<Cpu className="h-4 w-4" />}
            actions={
              model ? (
                <Badge tone="clean">{model.status ?? "ACTIVE"}</Badge>
              ) : (
                <Badge tone="stego">Unavailable</Badge>
              )
            }
          />
          <CardBody>
            {model ? (
              <div className="grid gap-6 lg:grid-cols-2">
                <dl className="space-y-2.5 text-xs">
                  <ModelRow label="Name" value={model.name} />
                  <ModelRow label="Version" value={model.version} />
                  <ModelRow label="Task type" value={model.task_type ?? "—"} />
                  <ModelRow
                    label="Architecture"
                    value={model.architecture ?? "—"}
                  />
                  <ModelRow label="Framework" value={model.framework ?? "—"} />
                  <ModelRow
                    label="Registered"
                    value={formatDateTime(model.created_at)}
                  />
                  <ModelRow
                    label="Artifact path"
                    value={model.artifact_path ?? "—"}
                    mono
                  />
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-faint">Artifact on disk</dt>
                    <dd>
                      <Badge tone={model.artifact_available ? "clean" : "stego"}>
                        {model.artifact_available ? "Present" : "Missing"}
                      </Badge>
                    </dd>
                  </div>
                </dl>

                <div className="space-y-3">
                  {model.description && (
                    <div className="rounded-lg border border-line bg-elevated/40 p-3">
                      <p className="text-[11px] uppercase tracking-wide text-faint">
                        Description
                      </p>
                      <p className="mt-1 text-xs leading-relaxed text-muted">
                        {model.description}
                      </p>
                    </div>
                  )}

                  <div className="flex items-start gap-2 rounded-lg border border-warn/40 bg-warn/10 p-3">
                    <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn" />
                    <p className="text-[11px] leading-relaxed text-muted">
                      Detector performance is payload-dependent. Confidence
                      values describe individual classifications and should not
                      be read as the model&apos;s overall accuracy. Candidate
                      regions are anomaly rankings, not confirmed embedding
                      locations.
                    </p>
                  </div>

                  {model.configuration &&
                    Object.keys(model.configuration).length > 0 && (
                      <details className="rounded-lg border border-line bg-elevated/40">
                        <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-muted">
                          Model configuration
                        </summary>
                        <pre className="max-h-64 overflow-auto border-t border-line px-3 py-2.5 font-mono text-[11px] leading-relaxed text-muted">
                          {JSON.stringify(model.configuration, null, 2)}
                        </pre>
                      </details>
                    )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted">
                {modelError ??
                  "No active steganalysis model is currently registered."}
              </p>
            )}
          </CardBody>
        </Card>
      </div>
    </AppLayout>
  );
}

function HealthRow({
  label,
  icon,
  state,
  checking,
}: {
  label: string;
  icon: React.ReactNode;
  state: boolean | null;
  checking: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2.5">
      <span className="flex items-center gap-2 text-xs font-medium text-fg">
        <span className="text-faint">{icon}</span>
        {label}
      </span>
      {checking && state === null ? (
        <Spinner className="h-3.5 w-3.5" />
      ) : (
        <Badge tone={state ? "clean" : "stego"}>
          {state ? "Reachable" : "Unreachable"}
        </Badge>
      )}
    </div>
  );
}

function ModelRow({
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
      <dt className="shrink-0 text-faint">{label}</dt>
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
