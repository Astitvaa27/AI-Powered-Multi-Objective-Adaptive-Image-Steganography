import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Moon, Radar, Sun } from "lucide-react";
import { ApiError } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Field";

export function SignupPage() {
  const navigate = useNavigate();
  const { signUp, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (!email.trim() || !password) {
      setError("Enter an email address and a password.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await signUp(email.trim(), password);
      navigate(`/verify-otp?email=${encodeURIComponent(email.trim())}`);
    } catch (exception) {
      setError(
        exception instanceof ApiError
          ? exception.message
          : "Sign up failed. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-full w-full">
      {/* Brand panel — hidden on small screens so the form gets the space. */}
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden bg-surface p-12 lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, rgb(var(--fg)) 1px, transparent 0)",
            backgroundSize: "28px 28px",
          }}
          aria-hidden
        />

        <div className="relative flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-white dark:text-[rgb(var(--bg))]">
            <Radar className="h-4 w-4" />
          </span>
          <span className="text-sm font-semibold tracking-tight">StegoLab</span>
        </div>

        <div className="relative max-w-lg">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight text-fg">
            AI-Powered Multi-Objective Adaptive Image Steganography &amp;
            Steganalysis
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            Embed payloads across LSB, DCT and DWT methods with measured
            distortion, then run Random Forest steganalysis to classify images
            and rank candidate anomaly regions.
          </p>

          <ul className="mt-8 space-y-2.5 text-xs text-muted">
            {[
              "Multi-objective embedding optimisation with PSNR, SSIM and MSE",
              "18-feature Random Forest steganalysis classifier",
              "Candidate region ranking from local LSB anomalies",
              "Persistent analysis sessions, predictions and reports",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-[11px] text-faint">
          Detector performance is payload-dependent. Results are statistical
          classifications, not proof of hidden content.
        </p>
      </div>

      <div className="flex w-full flex-col items-center justify-center px-6 lg:w-[30rem] lg:border-l lg:border-line">
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
          <div className="mb-8 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-white dark:text-[rgb(var(--bg))]">
              <Radar className="h-5 w-5" />
            </span>
          </div>

          <h2 className="text-xl font-semibold tracking-tight text-fg">
            Create your account
          </h2>
          <p className="mt-1 text-xs text-muted">
            We&apos;ll email you a verification code to confirm it&apos;s you.
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
              <Label htmlFor="password" hint="min. 8 characters">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                minLength={8}
                required
              />
            </div>

            <div>
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <Input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="••••••••"
                minLength={8}
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
              Create account
            </Button>
          </form>

          <p className="mt-6 text-[11px] leading-relaxed text-faint">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
