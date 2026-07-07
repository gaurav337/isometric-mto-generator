export enum ItemCategory {
  PIPE = "PIPE",
  FITTING = "FITTING",
  FLANGE = "FLANGE",
  VALVE = "VALVE",
  GASKET = "GASKET",
  BOLT = "BOLT",
  SUPPORT = "SUPPORT",
  WELD = "WELD",
}

export enum ItemUnit {
  M = "M",
  EA = "EA",
  SET = "SET",
}

export enum JobStatus {
  PENDING = "PENDING",
  RUNNING = "RUNNING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

export interface DrawingMetadata {
  drawing_no: string;
  revision: string;
  line_number: string;
  nps: string;
  material_class: string;
  service: string;
  design_pressure?: string | null;
  design_temperature?: string | null;
}

export interface MTOItem {
  item_no: number;
  category: ItemCategory;
  description: string;
  size_nps: string;
  schedule_rating?: string | null;
  material_spec?: string | null;
  end_type?: string | null;
  quantity: number;
  unit: ItemUnit;
  length_m?: number | null;
  confidence?: number | null;
  remarks: string;
}

export interface MTOSummary {
  total_pipe_length_m: number;
  fittings: number;
  flanges: number;
  valves: number;
  gaskets: number;
  bolt_sets: number;
  field_welds: number;
  supports: number;
}

export interface MTOResponse {
  job_id: string;
  status: JobStatus;
  source: "nvidia" | "gemini" | "mock";
  image_b64?: string | null;
  drawing_meta?: DrawingMetadata | null;
  items: MTOItem[];
  summary?: MTOSummary | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface UploadResponse {
  job_id: string;
  status: JobStatus;
}

export interface ErrorResponse {
  detail: string;
  code?: string | null;
}
