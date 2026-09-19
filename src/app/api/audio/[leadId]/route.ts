/**
 * Real audio proxy (brief §5-6). Streams actual WAV bytes from the FastAPI
 * backend's `/api/leads/{leadId}/audio` — never a fake/simulated playback
 * state. Exists as a Next.js route so `BACKEND_URL` stays a server-only
 * env var (never exposed to the browser, same rule as never shipping
 * ANTHROPIC_API_KEY to the frontend — see CLAUDE.md/backend config) while
 * the browser's <audio> element still gets a same-origin URL it can fetch
 * and Range-seek directly.
 */
import { NextRequest } from "next/server";

const BASE_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest, { params }: { params: Promise<{ leadId: string }> }) {
  const { leadId } = await params;
  const range = request.headers.get("range");

  const backendRes = await fetch(new URL(`/api/leads/${leadId}/audio`, BASE_URL), {
    headers: range ? { range } : undefined,
    cache: "no-store",
  });

  if (!backendRes.ok) {
    return new Response(null, { status: backendRes.status });
  }

  // Buffered rather than piped: these are small demo files (single-digit
  // MB), and buffering sidesteps stream-abort edge cases entirely when the
  // browser cancels an in-flight audio fetch mid-request (a normal thing
  // <audio> elements do while seeking/probing) — a bare pipe of
  // backendRes.body into the outer Response can throw an unhandled error
  // on the underlying dev server when that happens.
  const body = await backendRes.arrayBuffer();

  const headers = new Headers();
  for (const key of ["content-type", "content-length", "content-range", "accept-ranges"]) {
    const value = backendRes.headers.get(key);
    if (value) headers.set(key, value);
  }

  return new Response(body, { status: backendRes.status, headers });
}
