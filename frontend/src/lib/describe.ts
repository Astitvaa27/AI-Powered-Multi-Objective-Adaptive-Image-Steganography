/**
 * Plain-language wording shared across StegoLab. Technical names stay
 * available (e.g. in tooltips) but the primary label is beginner-friendly.
 */

export type MethodCode = "LSB" | "DCT" | "DWT";

export const METHOD_INFO: Record<MethodCode, { name: string; short: string; summary: string }> = {
  LSB: {
    name: "Pixel bits (LSB)",
    short: "LSB",
    summary:
      "Changes the last bit of pixel colour values. Highest capacity and least visible, but easiest for LSB detectors to spot.",
  },
  DCT: {
    name: "Frequency blocks (DCT)",
    short: "DCT",
    summary:
      "Hides bits in 8×8 blocks of the image's frequency data (blue channel). Low capacity; more noticeable, can survive mild JPEG re-saving.",
  },
  DWT: {
    name: "Wavelet detail (DWT)",
    short: "DWT",
    summary:
      "Hides bits in the fine-detail wavelet layer of the blue channel. Medium capacity.",
  },
};

export function methodName(method: string | null | undefined): string {
  if (!method) return "Unknown method";
  return METHOD_INFO[method.toUpperCase() as MethodCode]?.name ?? method;
}

/** e.g. "Pixel bits (LSB) · RGB, 1 bit" */
export function methodWithParams(
  method: string | null | undefined,
  channelMode?: string | null,
  lsbBits?: number | null,
): string {
  const base = methodName(method);
  if ((method ?? "").toUpperCase() !== "LSB" || !channelMode) return base;
  const channel = channelMode === "RGB" ? "all colours" : `${channelMode} channel`;
  return `${base} · ${channel}, ${lsbBits ?? 1} bit${(lsbBits ?? 1) > 1 ? "s" : ""}`;
}

export const IMAGE_KIND_LABEL: Record<string, string> = {
  COVER: "Original",
  STEGO: "Has hidden message",
  SUSPECT: "Uploaded for analysis",
};

export function imageKindLabel(kind: string | null | undefined): string | null {
  if (!kind) return null;
  return IMAGE_KIND_LABEL[kind.toUpperCase()] ?? null;
}

/**
 * Rule-of-thumb reading of PSNR (higher = closer to the original).
 * These bands are common guidelines, not guarantees.
 */
export function psnrVerdict(psnr: number | null | undefined): {
  label: string;
  tone: "clean" | "warn" | "stego";
} {
  if (psnr === null || psnr === undefined) return { label: "Identical to the original", tone: "clean" };
  if (psnr >= 50) return { label: "Invisible to the eye", tone: "clean" };
  if (psnr >= 40) return { label: "Practically invisible", tone: "clean" };
  if (psnr >= 30) return { label: "Hard to notice", tone: "warn" };
  return { label: "May be visible", tone: "stego" };
}

/** How to read a STEGO-class probability from the detector. */
export function detectionVerdict(stegoProbability: number | null | undefined): {
  label: string;
  tone: "clean" | "warn" | "stego";
} {
  if (stegoProbability === null || stegoProbability === undefined) {
    return { label: "Not measured", tone: "warn" };
  }
  if (stegoProbability >= 0.5) return { label: "Likely contains hidden data", tone: "stego" };
  return { label: "No hidden data detected", tone: "clean" };
}

export const PSNR_HELP =
  "Peak signal-to-noise ratio, in decibels. It compares the new image with the original: higher means fewer visible changes. Above about 40 dB the difference is generally invisible.";

export const SSIM_HELP =
  "Structural similarity, from 0 to 1. It measures whether shapes and textures still look the same. 1.0 means structurally identical.";

export const CHANGE_RATE_HELP =
  "The share of colour values that were modified at all. Fewer changed values usually means fewer statistical traces.";

export const CAPACITY_HELP =
  "How much of the method's available space the message used. Using less space usually leaves fewer traces.";

export const STEGO_PROBABILITY_HELP =
  "The detector's estimated probability that the image belongs to its 'contains hidden data' class. It is a statistical estimate, not proof — compare it with the original image's score.";

export const DETECTOR_SCOPE_NOTE =
  "The detector looks at statistics of the least significant bits of pixel values. It is most sensitive to pixel-bit (LSB) hiding and may not react to other methods.";
