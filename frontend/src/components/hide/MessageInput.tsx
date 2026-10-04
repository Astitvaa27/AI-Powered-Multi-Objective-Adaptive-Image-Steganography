import { useRef, useState } from "react";
import { FileText } from "lucide-react";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/cn";
import { Field, Textarea } from "@/components/ui/Field";

// Text files only: the backend hides UTF-8 text payloads.
const MAX_FILE_BYTES = 1024 * 1024;

export function MessageInput({
  value,
  onChange,
  error,
  capacityBytes,
}: {
  value: string;
  onChange: (value: string) => void;
  error?: string | null;
  /** Known capacity for the chosen settings, if any. */
  capacityBytes?: number | null;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const bytes = new TextEncoder().encode(value).length;
  const over = capacityBytes !== null && capacityBytes !== undefined && bytes > capacityBytes;

  const loadFile = async (file: File | undefined) => {
    setFileError(null);
    if (!file) return;

    if (file.size > MAX_FILE_BYTES) {
      setFileError("That file is larger than 1 MB. Use a shorter text file.");
      return;
    }

    try {
      const text = await file.text();
      if (text.includes("�")) {
        setFileError("That file doesn't look like plain text. Only UTF-8 text can be hidden.");
        return;
      }
      onChange(text);
    } catch {
      setFileError("Couldn't read that file.");
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div>
      <Field
        label="Secret message"
        hint={
          <span className={cn("tabular-nums", over && "text-stego")}>
            {formatBytes(bytes)}
            {capacityBytes ? ` of ${formatBytes(capacityBytes)}` : ""}
          </span>
        }
        labelAction={
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-accent hover:underline"
          >
            <FileText className="h-3.5 w-3.5" aria-hidden />
            Load .txt
          </button>
        }
        error={error ?? fileError ?? (over ? "This message is too long for the chosen settings." : null)}
        help="Plain text only. It's hidden, not encrypted — anyone with the image and StegoLab can read it."
      >
        <Textarea
          rows={4}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Type the message you want to hide…"
        />
      </Field>
      <input
        ref={fileRef}
        type="file"
        accept=".txt,text/plain"
        className="sr-only"
        aria-label="Load message from a text file"
        onChange={(event) => void loadFile(event.target.files?.[0])}
      />
    </div>
  );
}
