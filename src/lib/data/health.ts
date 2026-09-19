import { apiGet } from "../api/client";

export interface BackendHealth {
  status: string;
  database: string;
  dataMode: string;
  aiProvider: string;
  aiProviderConfigured: boolean;
  seeded: boolean;
  recordingsAvailable: number;
  sandboxConfigured: boolean;
}

/** Backs the developer diagnostics panel (brief §26-27) — never assume the
 * backend/database/AI provider are up; ask GET /api/health and show what
 * it actually reports. Returns a "backend unreachable" snapshot rather
 * than throwing, since this panel must never crash page render. */
export async function getHealth(): Promise<BackendHealth> {
  try {
    return await apiGet<BackendHealth>("/api/health");
  } catch {
    return {
      status: "unreachable",
      database: "unreachable",
      dataMode: "unknown",
      aiProvider: "unknown",
      aiProviderConfigured: false,
      seeded: false,
      recordingsAvailable: 0,
      sandboxConfigured: false,
    };
  }
}
