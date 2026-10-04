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
  /** Present on responses from the current backend. */
  mode?: "MANUAL" | "ADAPTIVE";
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
  /** RECORDED when method=AUTO used the method stored on the image. */
  method_source?: "RECORDED" | "REQUEST";
  channel_mode?: string | null;
  lsb_bits?: number | null;
  payload_size_bytes: number;
  payload_text: string;
  is_probably_text: boolean;
  processing_time_ms: number;
}

/* ---- Automatic detection and extraction ---- */

export type AutoValidation = "VERIFIED" | "PLAUSIBLE" | "UNVERIFIED";

export type AutoExtractStatus =
  | "VERIFIED"
  | "PLAUSIBLE"
  | "AMBIGUOUS"
  | "UNVERIFIED"
  | "NOT_FOUND";

export type AutoStageId =
  | "validate"
  | "records"
  | "containers"
  | "search"
  | "validate_candidates"
  | "steganalysis"
  | "result";

export interface AutoEvidence {
  check: string;
  passed: boolean;
  detail: string;
}

export interface AutoCandidate {
  id: string;
  adapter: string;
  adapter_name: string;
  method: string;
  family: "STEGOLAB" | "EXTERNAL" | "GENERIC";
  source: "PIXELS" | "FILE_STRUCTURE";
  configuration: string;
  parameters: Record<string, string | number | null>;
  validation: AutoValidation;
  explanation: string;
  evidence: AutoEvidence[];
  notes: string[];
  requires_key: boolean;
  key_hint: string | null;
  payload: {
    kind: "TEXT" | "BINARY";
    size_bytes: number;
    sha256: string;
    text: string | null;
    text_truncated: boolean;
    base64: string | null;
    detected_type: string | null;
    archive_entries: string[];
    truncated: boolean;
  };
  also_found_by: { adapter: string; adapter_name: string; configuration: string }[];
}

export interface AutoMethodTested {
  id: string;
  name: string;
  method: string;
  family: string;
  source: string;
  supported_inputs: string;
  detection: string;
  validation_rules: string;
  required_parameters: string[];
  limitations: string[];
  compatibility: string;
  applicable: boolean;
  skipped_reason: string | null;
  configurations_tested: number;
  configurations_total: number;
}

export interface AutoAttempt {
  adapter: string;
  adapter_name: string;
  configuration: string | null;
  outcome: "CANDIDATE" | "REJECTED" | "ERROR" | "SKIPPED" | "NOT_TESTED" | "SUPERSEDED" | "DUPLICATE";
  reason: string | null;
}

export interface AutoMetadataFinding {
  location: string;
  key: string;
  text: string;
  truncated: boolean;
  standard_key: boolean;
}

export interface AutoStageRecord {
  stage: AutoStageId;
  label: string;
  status: "completed" | "partial" | "skipped";
  duration_ms: number;
  detail: string | null;
}

export interface AutoExtractResult {
  image_id: string | null;
  status: AutoExtractStatus;
  extraction_succeeded: boolean;
  summary: string;
  best_candidate: AutoCandidate | null;
  candidates: AutoCandidate[];
  candidates_total: number;
  metadata_findings: AutoMetadataFinding[];
  image: {
    format: string;
    mime_type: string;
    width: number;
    height: number;
    mode: string;
    bit_depth: number | null;
    channels: string[];
    file_size_bytes: number;
    sha256: string;
    lossy: boolean;
    frame_count: number;
    pixels_readable: boolean;
    pixel_note: string | null;
    trailing_bytes: number;
  };
  record: {
    found: boolean;
    source?: "IMAGE_RECORD" | "HASH_MATCH";
    method?: string;
    channel_mode?: string | null;
    lsb_bits?: number | null;
    embedding_mode?: string;
    payload_hash_available?: boolean;
  };
  methods_tested: AutoMethodTested[];
  attempts: {
    total: number;
    by_outcome: Partial<Record<AutoAttempt["outcome"], number>>;
    details: AutoAttempt[];
  };
  steganalysis: {
    requested: boolean;
    available: boolean;
    ran: boolean;
    predicted_class: string | null;
    stego_probability: number | null;
    skipped_reason: string | null;
    note: string;
  };
  warnings: string[];
  limitations: string[];
  guidance: string[];
  ranking_basis: string;
  time_budget_reached: boolean;
  stages: AutoStageRecord[];
  processing_time_ms: number;
}

export type AutoExtractEvent =
  | {
      type: "stage";
      stage: AutoStageId;
      label: string;
      status: "running" | "completed" | "partial" | "skipped";
      detail: string | null;
      duration_ms?: number;
      progress?: { done: number; total: number };
    }
  | { type: "result"; result: AutoExtractResult }
  | { type: "error"; detail: string };

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
  method?: string | null;
  embedding_mode?: "MANUAL" | "ADAPTIVE" | null;
  optimization_run_id?: string | null;
}

export type ObjectiveName =
  | "quality"
  | "security"
  | "distortion"
  | "capacity"
  | "robustness";

export interface AdaptiveCandidate {
  key: string;
  label: string;
  method: "LSB" | "DCT" | "DWT";
  parameters: { channel_mode?: string; lsb_bits?: number };
  /** SKIPPED: payload did not fit. REJECTED: round-trip extraction failed. */
  status: "EVALUATED" | "SKIPPED" | "REJECTED" | "FAILED" | "PENDING";
  feasible: boolean;
  failure_reason: string | null;
  payload_size_bytes: number;
  capacity_bytes: number | null;
  capacity_used_ratio: number | null;
  extraction_verified: boolean | null;
  mse: number | null;
  psnr: number | null;
  ssim: number | null;
  change_rate: number | null;
  max_abs_change: number | null;
  stego_probability: number | null;
  steganalysis_class: string | null;
  robustness_bit_accuracy: number | null;
  objectives: Partial<Record<ObjectiveName, number>>;
  score: number | null;
  rank: number | null;
  pareto_optimal: boolean | null;
  selected: boolean;
  processing_time_ms: number | null;
  candidate_id?: string;
}

export interface AdaptiveSteganalysis {
  requested: boolean;
  available: boolean;
  analysis_session_id: string | null;
  predicted_class: string | null;
  stego_probability: number | null;
  confidence: number | null;
  cover_stego_probability: number | null;
  error: string | null;
}

/** The candidate comparison shared by live results and stored runs. */
export interface AdaptiveComparison {
  weights: Record<ObjectiveName, number>;
  objectives_evaluated: ObjectiveName[];
  candidates: AdaptiveCandidate[];
  explanation: string[];
  limitations: string[];
}

export interface AdaptiveEmbedResult extends EmbedResult, AdaptiveComparison {
  mode: "ADAPTIVE";
  selected_method: string;
  selected_candidate_key: string;
  selected_label: string;
  selected_score: number;
  change_rate: number | null;
  optimization_run_id: string;
  algorithm: string;
  steganalysis: AdaptiveSteganalysis;
}

/** GET /steganography/adaptive/runs/{id}: a stored adaptive run. */
export interface AdaptiveRunDetail extends AdaptiveComparison {
  optimization_run_id: string;
  status: string;
  cover_image_id: string;
  payload_id: string | null;
  algorithm: string;
  best_score: number | null;
  processing_time_ms: number | null;
  created_at: string;
  selected_method?: string;
  selected_candidate_key?: string;
  selected_parameters?: { channel_mode?: string; lsb_bits?: number };
  cover_stego_probability?: number | null;
  steganalysis_available?: boolean;
  steganography_session_id?: string;
  stego_image_id?: string;
  steganalysis?: AdaptiveSteganalysis;
}
