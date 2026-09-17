import { Container } from "@cloudflare/containers";

const SESSION_COOKIE = "swipecut_session";
const SESSION_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export class SwipeCutContainer extends Container {
  defaultPort = 8000;
  sleepAfter = "15m";
  enableInternet = false;
  envVars = {
    PORT: "8000",
    UPLOAD_DIR: "/tmp/swipecut/original",
    SEGMENTS_DIR: "/tmp/swipecut/segments",
    EXPORT_DIR: "/tmp/swipecut/export",
    DATABASE_URL: "sqlite:////tmp/swipecut/swipecut.db",
    MAX_UPLOAD_BYTES: String(95 * 1024 * 1024),
  };

  override onError(error: unknown): void {
    console.error(JSON.stringify({ event: "container_error", error: String(error) }));
  }
}

function readSessionId(request: Request): string | null {
  const cookie = request.headers.get("cookie") ?? "";
  for (const part of cookie.split(";")) {
    const [name, ...valueParts] = part.trim().split("=");
    if (name !== SESSION_COOKIE) continue;
    const value = valueParts.join("=");
    return SESSION_PATTERN.test(value) ? value : null;
  }
  return null;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const existingSessionId = readSessionId(request);
    const sessionId = existingSessionId ?? crypto.randomUUID();
    const container = env.SWIPECUT_CONTAINER.getByName(sessionId);

    try {
      const upstream = await container.fetch(request);
      if (existingSessionId) return upstream;

      const response = new Response(upstream.body, upstream);
      response.headers.append(
        "Set-Cookie",
        `${SESSION_COOKIE}=${sessionId}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=86400`,
      );
      return response;
    } catch (error) {
      console.error(JSON.stringify({ event: "proxy_error", error: String(error) }));
      return Response.json(
        { detail: "SwipeCutの起動に失敗しました。少し待ってから再度お試しください。" },
        { status: 503 },
      );
    }
  },
} satisfies ExportedHandler<Env>;
