import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Field, Input } from "@/components/ui/Field";
import { PasswordInput } from "@/components/ui/PasswordInput";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn, isAuthenticated, sessionExpired, clearSessionExpired } =
    useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [unverified, setUnverified] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Set by the reset-password page after a successful reset.
  const [passwordReset] = useState(
    () => (location.state as { passwordReset?: boolean } | null)?.passwordReset === true,
  );

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  // Clear the flag so a refresh doesn't show the banner again.
  useEffect(() => {
    if (passwordReset) navigate(location.pathname, { replace: true, state: null });
  }, [passwordReset, navigate, location.pathname]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;

    const errors: typeof fieldErrors = {};
    if (!EMAIL_PATTERN.test(email.trim())) errors.email = "Enter the email address you signed up with.";
    if (!password) errors.password = "Enter your password.";
    setFieldErrors(errors);
    if (errors.email || errors.password) return;

    setSubmitting(true);
    setError(null);
    setUnverified(false);
    clearSessionExpired();

    try {
      await signIn(email.trim(), password);
      navigate("/", { replace: true });
    } catch (exception) {
      if (exception instanceof ApiError && exception.status === 403 && /verif/i.test(exception.message)) {
        setUnverified(true);
      } else {
        setError(
          exception instanceof ApiError
            ? exception.message
            : "Sign in failed. Please try again.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      pageTitle="Sign in"
      title="Welcome back"
      description="Sign in to continue to StegoLab."
      footer={
        <>
          New to StegoLab?{" "}
          <Link to="/signup" className="font-medium text-accent hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <div className="space-y-4">
        {passwordReset && (
          <Callout tone="success" role="status" title="Password updated">
            Sign in with your new password.
          </Callout>
        )}
        {sessionExpired && !passwordReset && (
          <Callout tone="warning" role="status" title="You were signed out">
            Your session expired. Please sign in again.
          </Callout>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Field label="Email" error={fieldErrors.email}>
            <Input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoFocus
            />
          </Field>

          <Field
            label="Password"
            error={fieldErrors.password}
            labelAction={
              <Link
                to="/forgot-password"
                className="text-sm font-medium text-accent hover:underline"
              >
                Forgot password?
              </Link>
            }
          >
            <PasswordInput
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>

          {unverified && (
            <Callout tone="warning" role="alert" title="Verify your email first">
              Your account isn&apos;t active yet.{" "}
              <Link
                to={`/verify-otp?email=${encodeURIComponent(email.trim())}`}
                className="font-medium text-accent hover:underline"
              >
                Enter your verification code
              </Link>{" "}
              or request a new one.
            </Callout>
          )}

          {error && (
            <Callout tone="danger" role="alert">
              {error}
            </Callout>
          )}

          <Button type="submit" size="lg" className="w-full" loading={submitting}>
            Sign in
          </Button>
        </form>
      </div>
    </AuthLayout>
  );
}
