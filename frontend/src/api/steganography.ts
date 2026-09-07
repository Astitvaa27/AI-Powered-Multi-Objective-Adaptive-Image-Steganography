import { request } from "./client";
import type {
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

export function listSteganographySessions(params?: {
  limit?: number;
  offset?: number;
}): Promise<Paginated<SteganographySessionSummary>> {
  return request<Paginated<SteganographySessionSummary>>(
    "/steganography/sessions",
    { params },
  );
}
