import { request } from "./client";
import type {
  AnalysisResult,
  AnalysisSessionDetail,
  AnalysisSessionSummary,
  ModelInfo,
  Paginated,
  SteganalysisStats,
} from "./types";

export function analyzeImage(imageId: string): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/steganalysis/analyze/${imageId}`, {
    method: "POST",
  });
}

export function getActiveModel(): Promise<ModelInfo> {
  return request<ModelInfo>("/steganalysis/model");
}

export function getStats(): Promise<SteganalysisStats> {
  return request<SteganalysisStats>("/steganalysis/stats");
}

export function listSessions(params?: {
  limit?: number;
  offset?: number;
  predicted_class?: string;
}): Promise<Paginated<AnalysisSessionSummary>> {
  return request<Paginated<AnalysisSessionSummary>>("/steganalysis/sessions", {
    params,
  });
}

export function getSession(
  analysisSessionId: string,
): Promise<AnalysisSessionDetail> {
  return request<AnalysisSessionDetail>(
    `/steganalysis/sessions/${analysisSessionId}`,
  );
}
