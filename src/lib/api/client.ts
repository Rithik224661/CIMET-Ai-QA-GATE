/**
 * Centralized fetch wrapper for the FastAPI backend. This is the ONLY place
 * a raw `fetch` to the backend should appear — every function in
 * lib/data/*.ts and lib/actions/*.ts goes through apiGet/apiPost so the
 * base URL, error handling and JSON parsing live in one spot.
 */

const BASE_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(
  path: string,
  searchParams?: Record<string, string | undefined>,
): Promise<T> {
  const url = new URL(path, BASE_URL);
  if (searchParams) {
    for (const [k, v] of Object.entries(searchParams)) {
      if (v != null) url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new ApiError(`GET ${path} failed: ${res.status}`, res.status);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(new URL(path, BASE_URL), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(`POST ${path} failed: ${res.status}`, res.status);
  return res.json() as Promise<T>;
}
