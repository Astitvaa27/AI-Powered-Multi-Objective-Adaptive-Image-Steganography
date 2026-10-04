import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { MailCheck } from "lucide-react";
import { ApiError } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Field, Input } from "@/components/ui/Field";

// Matches the backend's OTP_RESEND_COOLDOWN_SECONDS default.
const RESEND_COOLDOWN_SECONDS = 60;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function VerifyOtpPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { verifyOtp, resendOtp, isAuthenticated } = useAuth();
  const { notify } = useToast();

  const initialEmail = searchParams.get("email") ?? "";
  const [email, setEmail] = useState(initialEmail);
  const [editingEmail, setEditingEmail] = useState(!initialEmail);
  const [otp, setOtp] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; otp?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  // A code was just sent when arriving from signup.
  const [cooldown, setCooldown] = useState(initialEmail ? RESEND_COOLDOWN_SECONDS : 0);

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
    if (submitting) return;

    const errors: typeof fieldErrors = {};
    if (!EMAIL_PATTERN.test(email.trim())) errors.email = "Enter the email you signed up with.";
    if (otp.length !== 6) errors.otp = "Enter all 6 digits from the email.";
    setFieldErrors(errors);
    if (errors.email || errors.otp) return;

    setSubmitting(true);
    setError(null);

    try {
      await verifyOtp(email.trim(), otp);
      navigate("/", { replace: true });
    } catch (exception) {
      setError(
        exception instanceof ApiError
          ? exception.message
          : "Verification failed. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || resending) return;

    if (!EMAIL_PATTERN.test(email.trim())) {
      setFieldErrors({ email: "Enter your email so we know where to send the code." });
      setEditingEmail(true);
      return;
    }

    setResending(true);
    setError(null);

    try {
      await resendOtp(email.trim());
      notify("A new code is on its way.", "success");
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (exception) {
      setError(
        exception instanceof ApiError
          ? exception.message
          : "Could not resend the code. Please try again.",
      );
    } finally {
      setResending(false);
    }
  };

  return (
    <AuthLayout
      pageTitle="Verify email"
      icon={<MailCheck className="h-6 w-6" />}
      title="Check your email"
      description={
        editingEmail ? (
          "Enter your email and the 6-digit code we sent you."
        ) : (
          <>
            We sent a 6-digit code to{" "}
            <span className="font-medium text-fg">{email}</span>. It expires in
            10 minutes.{" "}
            <button
              type="button"
              onClick={() => setEditingEmail(true)}
              className="font-medium text-accent hover:underline"
            >
              Change email
            </button>
          </>
        )
      }
      footer={
        <>
          Wrong account?{" "}
          <Link to="/signup" className="font-medium text-accent hover:underline">
            Start over
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {editingEmail && (
          <Field label="Email" error={fieldErrors.email}>
            <Input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </Field>
        )}

        <Field label="Verification code" error={fieldErrors.otp}>
          <Input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={otp}
            onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))}
            placeholder="000000"
            className="h-12 text-center font-mono text-xl tracking-[0.5em]"
            maxLength={6}
            autoFocus={!editingEmail}
          />
        </Field>

        {error && (
          <Callout tone="danger" role="alert">
            {error}
          </Callout>
        )}

        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          Verify and continue
        </Button>

        <p className="text-center text-sm text-muted">
          Didn&apos;t get it? Check spam, or{" "}
          <button
            type="button"
            onClick={() => void handleResend()}
            disabled={cooldown > 0 || resending}
            className="font-medium text-accent hover:underline disabled:cursor-not-allowed disabled:text-faint disabled:no-underline"
          >
            {cooldown > 0 ? `resend in ${cooldown}s` : resending ? "sending…" : "send a new code"}
          </button>
        </p>
      </form>
    </AuthLayout>
  );
}
