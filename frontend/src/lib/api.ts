import type {
  AlertDetail,
  AlertSummary,
  AssignCaseRequest,
  CaseRecord,
  CreateCaseRequest,
  EvidencePayload,
  ExportCaseResponse,
  RiskTier,
} from "@/types/api";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export class TraceXApiClientError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "TraceXApiClientError";
    this.status = status;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...options.headers,
      },
      cache: "no-store",
    });

    if (!res.ok) {
      let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const json = await res.json();
        if (json.detail) {
          errorMsg = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail);
        }
      } catch {
        // use fallback text
      }
      throw new TraceXApiClientError(errorMsg, res.status);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof TraceXApiClientError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : String(err);
    throw new TraceXApiClientError(
      `Cannot connect to Trace-X backend at ${API_BASE_URL}: ${message}`
    );
  }
}

export const api = {
  getBaseUrl(): string {
    return API_BASE_URL;
  },

  async checkHealth(): Promise<{ status: "connected" | "disconnected"; latencyMs: number }> {
    const start = performance.now();
    try {
      await fetch(`${API_BASE_URL}/alerts?min_tier=Low`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      const latencyMs = Math.round(performance.now() - start);
      return { status: "connected", latencyMs };
    } catch {
      return { status: "disconnected", latencyMs: 0 };
    }
  },

  async getAlerts(
    minTier: RiskTier | "All" = "Low",
    scenarioType?: string
  ): Promise<AlertSummary[]> {
    const params = new URLSearchParams();
    if (minTier && minTier !== "All") {
      params.append("min_tier", minTier);
    } else {
      params.append("min_tier", "Low");
    }
    if (scenarioType && scenarioType !== "All") {
      params.append("scenario_type", scenarioType.toLowerCase());
    }
    const query = params.toString() ? `?${params.toString()}` : "";
    return request<AlertSummary[]>(`/alerts${query}`);
  },

  async getAlert(accountId: string, includeBackground = false): Promise<AlertDetail> {
    const cleanId = encodeURIComponent(accountId.trim().toUpperCase());
    const query = includeBackground ? "?include_background=true" : "";
    return request<AlertDetail>(`/alerts/${cleanId}${query}`);
  },

  async getEvidence(accountId: string): Promise<EvidencePayload> {
    const cleanId = encodeURIComponent(accountId.trim().toUpperCase());
    return request<EvidencePayload>(`/alerts/${cleanId}/evidence`);
  },

  async getCases(): Promise<CaseRecord[]> {
    return request<CaseRecord[]>("/cases");
  },

  async getCase(caseId: string): Promise<CaseRecord> {
    const cleanId = encodeURIComponent(caseId.trim().toUpperCase());
    return request<CaseRecord>(`/cases/${cleanId}`);
  },

  async createCase(payload: CreateCaseRequest): Promise<CaseRecord> {
    return request<CaseRecord>("/cases", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async assignCase(caseId: string, reviewer: string): Promise<CaseRecord> {
    const cleanId = encodeURIComponent(caseId.trim().toUpperCase());
    const body: AssignCaseRequest = { reviewer: reviewer.trim() };
    return request<CaseRecord>(`/cases/${cleanId}/assign`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async exportCase(caseId: string): Promise<ExportCaseResponse> {
    const cleanId = encodeURIComponent(caseId.trim().toUpperCase());
    return request<ExportCaseResponse>(`/cases/${cleanId}/export`);
  },
};
