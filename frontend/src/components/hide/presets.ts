import type { ObjectiveName } from "@/api/types";

/**
 * Plain-language names for the optimiser's objectives. The backend scores
 * every candidate on each of these from 0 (worst) to 1 (best).
 */
export const OBJECTIVE_INFO: Record<ObjectiveName, { label: string; help: string }> = {
  quality: {
    label: "Image quality",
    help: "How close the result looks to the original (from PSNR and SSIM).",
  },
  security: {
    label: "Hard to detect",
    help: "1 minus the detector's probability that the image contains hidden data.",
  },
  distortion: {
    label: "Few changes",
    help: "How few colour values had to be modified.",
  },
  capacity: {
    label: "Spare room",
    help: "How much of the method's space was left unused.",
  },
  robustness: {
    label: "Survives JPEG",
    help: "How much of the message could still be read after re-saving the image as a JPEG.",
  },
};

export type PresetId = "balanced" | "stealth" | "quality" | "robust";

/**
 * Priority presets for automatic mode. "balanced" sends no weights so the
 * server's configured defaults apply; the others send explicit weights,
 * which the server normalises.
 */
export const HIDE_PRESETS: {
  id: PresetId;
  title: string;
  description: string;
  recommended?: boolean;
  weights?: Record<ObjectiveName, number>;
}[] = [
  {
    id: "balanced",
    title: "Balanced",
    description: "A sensible mix of quality, stealth and reliability.",
    recommended: true,
  },
  {
    id: "stealth",
    title: "Hardest to detect",
    description: "Prefers the result the detector finds least suspicious.",
    weights: { security: 0.55, quality: 0.2, distortion: 0.15, capacity: 0.05, robustness: 0.05 },
  },
  {
    id: "quality",
    title: "Best image quality",
    description: "Prefers the result that looks most like the original.",
    weights: { quality: 0.55, distortion: 0.25, security: 0.1, capacity: 0.05, robustness: 0.05 },
  },
  {
    id: "robust",
    title: "Survives compression",
    description: "Prefers messages that survive JPEG re-saving. Most methods don't.",
    weights: { robustness: 0.5, quality: 0.2, security: 0.2, distortion: 0.05, capacity: 0.05 },
  },
];
