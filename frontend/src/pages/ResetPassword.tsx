import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { KeyRound, ShieldAlert } from "lucide-react";
import { ApiError } from "@/api/client";
import { resetPassword, validateResetToken } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { PasswordRules, validateNewPassword } from "@/components/auth/PasswordRules";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Field } from "@/components/ui/Field";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { LoadingState } from "@/components/ui/States";

type LinkStatus = "checking" | "valid" | "invalid";

/**
 * The emailed link carries the token in the URL fragment (#token=...),
 * which browsers never send to servers. ?token= is accepted as a fallback.
 */
function readTokenFromUrl(): string | null {
  const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const query = new URLSearchParams(window.location.search);
  return fragment.get("token") ?? query.get("token");
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signOut } = useAuth();

  const [token] = useState(readTokenFromUrl);
  const [linkStatus, setLinkStatus] = useState<LinkStatus>(token ? "checking" : "invalid");
  const [linkError, setLinkError] = useState<string | null>(null);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ password: string | null; confirm: string | null }>({
    password: null,
    confirm: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Drop the token from the address bar and browser history once read.
  useEffect(() => {
    if (location.hash || location.search) {
      navigate(location.pathname, { replace: true });
    }
  }, [location.hash, location.search, location.pathname, navigate]);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    validateResetToken(token)
      .then(() => {
        if (!cancelled) setLinkStatus("valid");
      })
      .catch((exception) => {
        if (cancelled) return;
        setLinkStatus("invalid");
        setLinkError(
          exception instanceof ApiError && exception.status !== 0
            ? exception.message
            : "We couldn't check this link. Check your connection and open it again.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || submitting) return;

    const problems = validateNewPassword(password, confirmPassword);
    setFieldErrors(problems);
    if (problems.password || problems.confirm) return;

    setSubmitting(true);
    setError(null);

    try {
      await resetPassword(token, password, confirmPassword);
      // Every existing session was revoked by the reset.
      signOut();
      navigate("/login", { replace: true, state: { passwordReset: true } });
    } catch (exception) {
      const message =
        exception instanceof ApiError
          ? exception.message
          : "Could not reset your password. Please try again.";

      // A token rejected at this point (expired or used meanwhile) cannot
      // succeed on retry, so switch to the invalid-link view.
      if (exception instanceof ApiError && exception.status === 400) {
        setLinkStatus("invalid");
        setLinkError(message);
      } else {
        setError(message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (linkStatus === "checking") {
    return (
      <AuthLayout pageTitle="Reset password" icon={<KeyRound className="h-6 w-6" />} title="Reset your password">
        <LoadingState label="Checking your reset link…" className="py-6" />
      </AuthLayout>
    );
  }

  if (linkStatus === "invalid") {
    return (
      <AuthLayout
        pageTitle="Reset password"
        icon={<ShieldAlert className="h-6 w-6" />}
        title="This link can't be used"
        description={
          linkError ??
          "The reset link is incomplete. Open it directly from your email, or request a new one."
        }
        footer={
          <Link to="/login" className="font-medium text-accent hover:underline">
            Back to sign in
          </Link>
        }
      >
        <ButtonLink to="/forgot-password" size="lg" className="w-full">
          Request a new link
        </ButtonLink>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      pageTitle="Reset password"
      icon={<KeyRound className="h-6 w-6" />}
      title="Choose a new password"
      description="You'll be signed out on every device and can then sign in with the new password."
      footer={
        <Link to="/login" className="font-medium text-accent hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <Field label="New password" error={fieldErrors.password}>
          <PasswordInput
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoFocus
          />
        </Field>

        <Field label="Confirm new password" error={fieldErrors.confirm}>
          <PasswordInput
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
        </Field>

        <PasswordRules password={password} confirm={confirmPassword} />

        {error && (
          <Callout tone="danger" role="alert">
            {error}
          </Callout>
        )}

        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          Reset password
        </Button>
      </form>
    </AuthLayout>
  );
}
