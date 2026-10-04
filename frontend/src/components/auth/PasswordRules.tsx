import { Check, X } from "lucide-react";
import { cn } from "@/lib/cn";

// Matches the backend: at least 8 characters, and at most 72 bytes because
// bcrypt ignores anything beyond that.
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;

const byteLength = (value: string) => new TextEncoder().encode(value).length;

/** Returns the first problem with a new password, or null if it is valid. */
export function validateNewPassword(password: string, confirm: string): {
  password: string | null;
  confirm: string | null;
} {
  let passwordError: string | null = null;

  if (password.length < PASSWORD_MIN_LENGTH) {
    passwordError = `Use at least ${PASSWORD_MIN_LENGTH} characters.`;
  } else if (byteLength(password) > PASSWORD_MAX_BYTES) {
    passwordError = `Use at most ${PASSWORD_MAX_BYTES} bytes (fewer for emoji or accented characters).`;
  } else if (!password.trim()) {
    passwordError = "A password can't be only spaces.";
  }

  return {
    password: passwordError,
    confirm: password !== confirm ? "The passwords don't match." : null,
  };
}

/** Live checklist shown under new-password fields. */
export function PasswordRules({
  password,
  confirm,
  id,
}: {
  password: string;
  confirm: string;
  id?: string;
}) {
  const tooLong = byteLength(password) > PASSWORD_MAX_BYTES;
  const rules = [
    { label: `At least ${PASSWORD_MIN_LENGTH} characters`, met: password.length >= PASSWORD_MIN_LENGTH },
    { label: "Both passwords match", met: password.length > 0 && password === confirm },
  ];

  return (
    <ul id={id} className="space-y-1 text-xs" aria-live="polite">
      {rules.map((rule) => (
        <li
          key={rule.label}
          className={cn("flex items-center gap-1.5", rule.met ? "text-clean" : "text-muted")}
        >
          {rule.met ? (
            <Check className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <X className="h-3.5 w-3.5 text-faint" aria-hidden />
          )}
          {rule.label}
          <span className="sr-only">{rule.met ? "(done)" : "(not yet)"}</span>
        </li>
      ))}
      {tooLong && (
        <li className="flex items-center gap-1.5 text-stego">
          <X className="h-3.5 w-3.5" aria-hidden />
          No more than {PASSWORD_MAX_BYTES} bytes
        </li>
      )}
    </ul>
  );
}
