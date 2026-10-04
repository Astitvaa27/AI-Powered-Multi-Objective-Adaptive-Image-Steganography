import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, KeyRound, MailCheck } from "lucide-react";
import { ApiError } from "@/api/client";
import { forgotPassword } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Field, Input } from "@/components/ui/Field";

// Mirrors the backend's per-account cooldown between reset emails.
const RESEND_COOLDOWN_SECONDS = 60;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [email, setEmail] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting || cooldown > 0) return;

    if (!EMAIL_PATTERN.test(email.trim())) {
      setFieldError("Enter a valid email address.");
      return;
    }

    setFieldError(null);
    setSubmitting(true);
    setError(null);

    try {
      const response = await forgotPassword(email.trim());
      setConfirmation(response.message);
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (exception) {
      setError(
        exception instanceof ApiError
          ? exception.message
          : "Could not send the request. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      pageTitle="Forgot password"
      icon={confirmation ? <MailCheck className="h-6 w-6" /> : <KeyRound className="h-6 w-6" />}
      title={confirmation ? "Check your email" : "Reset your password"}
      description={
        confirmation
          ? "Open the link in the email to choose a new password."
          : "Enter the email you signed up with and we'll send you a reset link."
      }
      footer={
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 font-medium text-accent hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {confirmation && (
          <Callout tone="success" role="status">
            {confirmation} The link expires after a short time and works once.
            Check your spam folder if it doesn&apos;t arrive.
          </Callout>
        )}

        <Field label="Email" error={fieldError}>
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoFocus
          />
        </Field>

        {error && (
          <Callout tone="danger" role="alert">
            {error}
          </Callout>
        )}

        <Button
          type="submit"
          size="lg"
          className="w-full"
          variant={confirmation ? "secondary" : "primary"}
          loading={submitting}
          disabled={cooldown > 0}
        >
          {confirmation
            ? cooldown > 0
              ? `Send again in ${cooldown}s`
              : "Send the link again"
            : "Send reset link"}
        </Button>
      </form>
    </AuthLayout>
  );
}
