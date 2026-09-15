export interface ModelProfile {
  threads: number;
  ctx_size: number;
  n_gpu_layers: number;
  extra_args: string;
  notes?: string[];
}

export interface ServerStatus {
  status: "running" | "starting" | "stopped";
  pid: number | null;
  state: Record<string, unknown>;
  http: { reachable: boolean; ok: boolean };
  log_path: string;
}

export interface ServerLogResponse {
  tail: string;
}

export interface ServerMetrics {
  running: boolean;
  pid: number | null;
  process?: { cpu_percent: number; rss_bytes: number | null; cpu_seconds: number };
  llama?: { slots_idle?: number; slots_processing?: number; cache_tokens?: number };
}

export interface LogStreamEvent {
  text: string;
}

export interface ChatRequest {
  prompt: string;
  temperature: number;
  max_tokens: number;
}

export interface StreamEvent {
  choices?: Array<{
    delta?: { content?: string };
    finish_reason?: string | null;
  }>;
  error?: string;
}

declare global {
  interface Window {
    SERVER_PROFILES?: Record<number, ModelProfile>;
  }
}
