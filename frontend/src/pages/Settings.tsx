import { useState } from "react";
import { Cpu, LogOut, Monitor, Moon, Server, Sun, UserRound } from "lucide-react";
import { checkDatabaseHealth, checkHealth, forgotPassword } from "@/api/auth";
import { API_BASE_URL } from "@/api/client";
import { getActiveModel } from "@/api/steganalysis";
import { useAuth } from "@/context/AuthContext";
import { useTheme, type ThemePreference } from "@/context/ThemeContext";
import { errorMessage, useAsync } from "@/hooks/useAsync";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { AppLayout } from "@/components/layout/AppLayout";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Collapsible } from "@/components/ui/Collapsible";
import { Spinner } from "@/components/ui/States";

const THEMES: { value: ThemePreference; label: string; icon: typeof Sun; text: string }[] = [
  { value: "light", label: "Light", icon: Sun, text: "Bright and high-contrast" },
  { value: "dark", label: "Dark", icon: Moon, text: "Easier on the eyes at night" },
  { value: "system", label: "System", icon: Monitor, text: "Match your device setting" },
];

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-3">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="min-w-0 text-sm text-fg">{children}</dd>
    </div>
  );
}

function AccountCard() {
  const { profile, signOut } = useAuth();
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<{ tone: "success" | "danger"; text: string } | null>(null);

  const sendReset = async () => {
    if (!profile?.email) return;
    setSending(true);
    setNotice(null);
    try {
      await forgotPassword(profile.email);
      setNotice({
        tone: "success",
        text: `If email delivery is working, a reset link is on its way to ${profile.email}. It expires shortly and works once.`,
      });
    } catch (exception) {
      setNotice({ tone: "danger", text: errorMessage(exception, "Couldn't send the reset link.") });
    } finally {
      setSending(false);
    }
  };

  return (
    <Card>
      <CardHeader icon={<UserRound className="h-4 w-4" />} title="Account" />
      <CardBody className="space-y-4">
        <dl className="divide-y divide-line">
          <Row label="Email">
            {profile ? <span className="break-all">{profile.email}</span> : <Spinner />}
          </Row>
          <Row label="Email verified">
            {profile ? (
              <Badge tone={profile.email_verified ? "clean" : "warn"}>
                {profile.email_verified ? "Verified" : "Not verified"}
              </Badge>
            ) : (
              "—"
            )}
          </Row>
          <Row label="Password">
            <Button variant="secondary" size="sm" onClick={() => void sendReset()} loading={sending} disabled={!profile}>
              Send password reset link
            </Button>
          </Row>
        </dl>
        {notice && (
          <Callout tone={notice.tone} role={notice.tone === "danger" ? "alert" : "status"}>
            {notice.text}
          </Callout>
        )}
        <p className="text-xs leading-relaxed text-muted">
          Resetting your password signs you out on every device.
        </p>
        <Button variant="ghost" onClick={signOut} className="-ml-3">
          <LogOut className="h-4 w-4" aria-hidden />
          Sign out
        </Button>
      </CardBody>
    </Card>
  );
}

function AppearanceCard() {
  const { preference, setPreference } = useTheme();

  return (
    <Card>
      <CardHeader icon={<Monitor className="h-4 w-4" />} title="Appearance" description="Saved in this browser." />
      <CardBody>
        <fieldset>
          <legend className="sr-only">Theme</legend>
          <div className="grid gap-2 sm:grid-cols-3">
            {THEMES.map(({ value, label, icon: Icon, text }) => (
              <label
                key={value}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent",
                  preference === value
                    ? "border-accent bg-accent-soft/60"
                    : "border-line hover:border-line-strong hover:bg-elevated/50",
                )}
              >
                <input
                  type="radio"
                  name="theme"
                  value={value}
                  checked={preference === value}
                  onChange={() => setPreference(value)}
                  className="sr-only"
                />
                <Icon className={cn("h-5 w-5 shrink-0", preference === value ? "text-accent" : "text-muted")} aria-hidden />
                <span>
                  <span className="block text-sm font-medium text-fg">{label}</span>
                  <span className="block text-xs text-muted">{text}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      </CardBody>
    </Card>
  );
}

function StatusBadge({ ok }: { ok: boolean }) {
  return <Badge tone={ok ? "clean" : "stego"}>{ok ? "Working" : "Unavailable"}</Badge>;
}

function SystemCard() {
  const { data, loading, reload } = useAsync(
    async () => {
      const [api, database, model] = await Promise.allSettled([
        checkHealth(),
        checkDatabaseHealth(),
        getActiveModel(),
      ]);
      return {
        api: api.status === "fulfilled",
        database: database.status === "fulfilled",
        model: model.status === "fulfilled" ? model.value : null,
        modelError: model.status === "rejected" ? errorMessage(model.reason, "Unavailable") : null,
      };
    },
    [],
  );

  return (
    <Card className="lg:col-span-2">
      <CardHeader
        icon={<Server className="h-4 w-4" />}
        title="System status"
        description="Whether the services StegoLab depends on are reachable."
        actions={
          <Button variant="secondary" size="sm" onClick={() => void reload()} loading={loading}>
            Check again
          </Button>
        }
      />
      <CardBody>
        {!data ? (
          <div className="flex justify-center py-6">
            <Spinner className="h-5 w-5" />
          </div>
        ) : (
          <dl className="divide-y divide-line">
            <Row label="StegoLab server">
              <StatusBadge ok={data.api} />
            </Row>
            <Row label="Database">
              <StatusBadge ok={data.database} />
            </Row>
            <Row label="Detection model (used by Analyze)">
              <StatusBadge ok={Boolean(data.model)} />
            </Row>
          </dl>
        )}
      </CardBody>
      {data && (
        <Collapsible title="Technical details" description="For troubleshooting">
          <dl className="divide-y divide-line">
            <Row label="API address">
              <span className="break-all font-mono text-xs">{API_BASE_URL}</span>
            </Row>
            {data.model ? (
              <>
                <Row label="Model">
                  {data.model.name} {data.model.version}
                </Row>
                <Row label="Type">{data.model.architecture ?? "—"}</Row>
                <Row label="Framework">{data.model.framework ?? "—"}</Row>
                <Row label="Registered">{formatDateTime(data.model.created_at)}</Row>
                <Row label="Model file on server">
                  <Badge tone={data.model.artifact_available ? "clean" : "stego"}>
                    {data.model.artifact_available ? "Present" : "Missing"}
                  </Badge>
                </Row>
                {data.model.description && <Row label="Description">{data.model.description}</Row>}
              </>
            ) : (
              <Row label="Model">{data.modelError ?? "Not registered"}</Row>
            )}
          </dl>
        </Collapsible>
      )}
    </Card>
  );
}

export function SettingsPage() {
  return (
    <AppLayout title="Settings" description="Your account, appearance and system status.">
      <div className="grid gap-6 lg:grid-cols-2">
        <AccountCard />
        <AppearanceCard />
        <SystemCard />
      </div>
      <p className="mt-6 flex items-center gap-1.5 text-xs text-muted">
        <Cpu className="h-3.5 w-3.5" aria-hidden />
        Detection results are statistical estimates and can be wrong.
      </p>
    </AppLayout>
  );
}
