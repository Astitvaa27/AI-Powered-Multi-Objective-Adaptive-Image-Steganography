export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface ImageRecord {
  id: string;
  original_filename: string;
  storage_path: string;
  mime_type: string;
  file_extension: string;
  file_size_bytes: number;
  width: number;
  height: number;
  channels: number;
  bit_depth: number | null;
  sha256_hash: string;
  metadata: Record<string, unknown>;
  status: string;
  created_at: string;
}

export interface Paginated<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export interface SuspiciousRegion {
  id?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  suspicion_score: number | null;
  region_type: string | null;
  metadata: Record<string, unknown>;
}

export type FeatureMap = Record<string, number>;

export interface ModelInfo {
  id: string;
  name: string;
  version: string;
  framework: string | null;
  architecture: string | null;
  task_type?: string;
  artifact_path?: string;
  artifact_available?: boolean;
  configuration?: Record<string, unknown>;
  description?: string | null;
  status?: string;
  created_at?: string;
}

export interface AnalysisResult {
  status: string;
  analysis_session_id: string;
  model_prediction_id: string;
  image_id: string;
  predicted_class: string;
  confidence: number;
  probabilities: Record<string, number>;
  processing_time_ms: number;
  feature_count: number;
  features: FeatureMap;
  suspicious_regions: SuspiciousRegion[];
  model?: ModelInfo | null;
  analysis_report: {
    id: string;
    report_type: string;
    title: string | null;
    summary: string | null;
    report_data: Record<string, unknown>;
    status: string;
  };
}

export interface AnalysisSessionSummary {
  analysis_session_id: string;
  image_id: string;
  image_filename: string | null;
  analysis_type: string;
  status: string;
  predicted_class: string | null;
  confidence: number | null;
  probabilities: Record<string, number> | null;
  processing_time_ms: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisSessionDetail {
  analysis_session_id: string;
  status: string;
  analysis_type: string;
  processing_time_ms: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  image: {
    id: string;
    original_filename: string;
    storage_path: string;
    width: number;
    height: number;
    channels: number;
    file_size_bytes: number;
    mime_type: string;
    file_extension: string;
    metadata: Record<string, unknown>;
  } | null;
  prediction: {
    id: string;
    predicted_class: string;
    confidence: number | null;
    probabilities: Record<string, number>;
    metadata: Record<string, unknown>;
  } | null;
  model: ModelInfo | null;
  features: FeatureMap | null;
  feature_count: number | null;
  suspicious_regions: SuspiciousRegion[];
  report: {
    id: string;
    report_type: string;
    title: string | null;
    summary: string | null;
    report_data: Record<string, unknown>;
    report_path: string | null;
    status: string;
    created_at: string;
  } | null;
}

export interface SteganalysisStats {
  total_analyses: number;
  completed_analyses: number;
  failed_analyses: number;
  clean_count: number;
  stego_count: number;
  total_images: number;
  total_candidate_regions: number;
  average_processing_time_ms: number | null;
  average_confidence: number | null;
}

export interface EmbeddingMethodInfo {
  code: "LSB" | "DCT" | "DWT";
  name: string;
  id: string | null;
  registered: boolean;
  supports: { channel_mode: boolean; lsb_bits: boolean };
}

export interface CapacityInfo {
  image_id: string;
  channel_mode: string;
  lsb_bits: number;
  capacity_bytes: number;
  width: number;
  height: number;
}

export interface EmbedResult {
  session_id: string;
  status: string;
  method: string;
  channel_mode: string | null;
  lsb_bits: number | null;
  cover_image_id: string;
  stego_image_id: string;
  payload_id: string;
  payload_size_bytes: number;
  capacity_bytes: number;
  capacity_used_ratio: number | null;
  mse: number;
  psnr: number | null;
  ssim: number;
  processing_time_ms: number;
  extraction_verified: boolean;
  extraction_accuracy: number;
  extracted_preview: string | null;
  output_path: string;
}

export interface ExtractResult {
  image_id: string;
  method: string;
  payload_size_bytes: number;
  payload_text: string;
  is_probably_text: boolean;
  processing_time_ms: number;
}

export interface SteganographySessionSummary {
  id: string;
  status: string;
  cover_image_id: string;
  cover_image_filename: string | null;
  stego_image_id: string | null;
  payload_id: string | null;
  payload_capacity_bytes: number | null;
  psnr: number | null;
  ssim: number | null;
  extraction_accuracy: number | null;
  processing_time_ms: number | null;
  error_message: string | null;
  created_at: string;
}
