import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Moon, ShieldCheck, Sun } from "lucide-react";
import { ApiError } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useToast } from "@/context/ToastContext";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Field";

const RESEND_COOLDOWN_SECONDS = 60;

export function VerifyOtpPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { verifyOtp, resendOtp, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { notify } = useToast();

  const [email, setEmail] = useState(searchParams.get("email") ?? "");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SECONDS);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setCooldown((current) => (current > 0 ? current - 1 : 0));
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (!email.trim() || otp.trim().length < 4) {
      setError("Enter your email and the verification code.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await verifyOtp(email.trim(), otp.trim());
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
    if (!email.trim() || cooldown > 0) return;

    setResending(true);
    setError(null);

    try {
      await resendOtp(email.trim());
      notify("A new verification code has been sent.", "success");
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
    <div className="flex h-full w-full items-center justify-center px-6">
      <div className="absolute right-5 top-5">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          className="h-9 w-9 p-0"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>
      </div>

      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent text-white dark:text-[rgb(var(--bg))]">
            <ShieldCheck className="h-6 w-6" />
          </span>
        </div>

        <h2 className="text-center text-xl font-semibold tracking-tight text-fg">
          Verify your email
        </h2>
        <p className="mt-1 text-center text-xs text-muted">
          Enter the verification code we sent to your email address. It
          expires in 10 minutes.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
          <div>
            <Label htmlFor="email">Email address</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="analyst@example.com"
              required
            />
          </div>

          <div>
            <Label htmlFor="otp">Verification code</Label>
            <Input
              id="otp"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={otp}
              onChange={(event) =>
                setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
              placeholder="123456"
              className="tracking-[0.3em] text-center font-mono"
              maxLength={6}
              required
            />
          </div>

          {error && (
            <p
              className="rounded-lg border border-stego/40 bg-stego/10 px-3 py-2.5 text-xs text-fg"
              role="alert"
            >
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" loading={submitting}>
            Verify &amp; continue
          </Button>
        </form>

        <div className="mt-5 text-center text-[11px] text-faint">
          Didn&apos;t get a code?{" "}
          <button
            type="button"
            onClick={handleResend}
            disabled={cooldown > 0 || resending}
            className="font-medium text-accent hover:underline disabled:cursor-not-allowed disabled:text-faint disabled:no-underline"
          >
            {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
          </button>
        </div>

        <p className="mt-6 text-center text-[11px] leading-relaxed text-faint">
          Wrong email?{" "}
          <Link to="/signup" className="font-medium text-accent hover:underline">
            Start over
          </Link>
        </p>
      </div>
    </div>
  );
}
