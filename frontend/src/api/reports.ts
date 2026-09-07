import { request } from "./client";

export interface AnalysisReportRecord {
  id: string;
  analysis_session_id: string;
  report_type: string;
  title: string | null;
  summary: string | null;
  report_data: Record<string, unknown>;
  report_path: string | null;
  status: string;
  created_at: string;
}

export function getReport(
  analysisSessionId: string,
): Promise<AnalysisReportRecord> {
  return request<AnalysisReportRecord>(
    `/steganalysis/reports/${analysisSessionId}`,
  );
}
