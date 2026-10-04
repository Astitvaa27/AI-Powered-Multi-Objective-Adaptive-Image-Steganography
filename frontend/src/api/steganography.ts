import { ApiError, request, requestNdjson } from "./client";
import type {
  AdaptiveEmbedResult,
  AdaptiveRunDetail,
  AutoExtractEvent,
  AutoExtractResult,
  CapacityInfo,
  EmbedResult,
  EmbeddingMethodInfo,
  ExtractResult,
  Paginated,
  SteganographySessionSummary,
} from "./types";

export function listMethods(): Promise<EmbeddingMethodInfo[]> {
  return request<EmbeddingMethodInfo[]>("/steganography/methods");
}

export function getCapacity(params: {
  image_id: string;
  channel_mode: string;
  lsb_bits: number;
}): Promise<CapacityInfo> {
  return request<CapacityInfo>("/steganography/capacity", { params });
}

export function embedPayload(body: {
  cover_image_id: string;
  method: string;
  payload_text: string;
  channel_mode: string;
  lsb_bits: number;
}): Promise<EmbedResult> {
  return request<EmbedResult>("/steganography/embed", {
    method: "POST",
    body,
  });
}

/**
 * Closed-loop adaptive embedding: the backend tries every candidate
 * method, scores them on several objectives and keeps the best one.
 */
export function adaptiveEmbed(body: {
  cover_image_id: string;
  payload_text: string;
  weights?: Partial<Record<string, number>>;
  run_steganalysis?: boolean;
}): Promise<AdaptiveEmbedResult> {
  return request<AdaptiveEmbedResult>("/steganography/adaptive/embed", {
    method: "POST",
    body,
  });
}

export function getAdaptiveRun(runId: string): Promise<AdaptiveRunDetail> {
  return request<AdaptiveRunDetail>(`/steganography/adaptive/runs/${runId}`);
}

/** method may be "AUTO" to use the method recorded on the stego image. */
export function extractPayload(body: {
  image_id: string;
  method: string;
  channel_mode: string;
  lsb_bits: number;
}): Promise<ExtractResult> {
  return request<ExtractResult>("/steganography/extract", {
    method: "POST",
    body,
  });
}

/**
 * Detect and extract without knowing the method. Streams real progress
 * events from the backend and resolves with the final result.
 */
export async function autoExtract(
  body: { image_id: string; run_steganalysis?: boolean },
  onEvent: (event: AutoExtractEvent) => void,
  signal?: AbortSignal,
): Promise<AutoExtractResult> {
  const formData = new FormData();
  formData.set("image_id", body.image_id);
  formData.set("run_steganalysis", String(body.run_steganalysis ?? true));

  // Filled from inside the event callback.
  const outcome: { result: AutoExtractResult | null; failure: string | null } = {
    result: null,
    failure: null,
  };

  await requestNdjson<AutoExtractEvent>("/steganography/extract/auto", {
    formData,
    params: { stream: true },
    signal,
    onEvent: (event) => {
      if (event.type === "result") outcome.result = event.result;
      else if (event.type === "error") outcome.failure = event.detail;
      onEvent(event);
    },
  });

  if (outcome.failure) throw new ApiError(500, outcome.failure);
  if (!outcome.result) {
    throw new ApiError(0, "The detection finished without a result. Please try again.");
  }
  return outcome.result;
}

export function listSteganographySessions(params?: {
  limit?: number;
  offset?: number;
}): Promise<Paginated<SteganographySessionSummary>> {
  return request<Paginated<SteganographySessionSummary>>(
    "/steganography/sessions",
    { params },
  );
}
