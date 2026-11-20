import { API_URL, getToken } from "@/lib/api";

type Handler = (event: string, data: unknown) => void;

/** Open an authenticated SSE stream. EventSource cannot set Authorization headers. */
export function openSSE(
  path: string,
  onEvent: Handler,
  onError?: (err: Event) => void,
): () => void {
  const token = getToken();
  if (!token) {
    onError?.(new Event("unauthorized"));
    return () => undefined;
  }
  const sep = path.includes("?") ? "&" : "?";
  const url = `${API_URL}${path}${sep}access_token=${encodeURIComponent(token)}`;
  const es = new EventSource(url);

  const wrap = (name: string) => (ev: MessageEvent) => {
    try {
      onEvent(name, JSON.parse(ev.data));
    } catch {
      onEvent(name, ev.data);
    }
  };

  // Named events from the API
  ["overview", "investigation", "error", "ping"].forEach((name) => {
    es.addEventListener(name, wrap(name) as EventListener);
  });
  es.onmessage = wrap("message");
  es.onerror = (err) => {
    onError?.(err);
  };

  return () => es.close();
}
