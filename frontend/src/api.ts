export interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}
export interface DetectedText {
  text: string;
  bbox: BBox;
}
export interface FillItem {
  label: string;
  value: string;
  target_phrase: string;
  bbox: BBox | null;
  point: [number, number] | null;
  reason: string | null;
}
export interface AutofillResponse {
  image_width: number;
  image_height: number;
  detected_texts: DetectedText[];
  plan: FillItem[];
  brain_model: string;
  eyes_model: string;
  mock: boolean;
}

export async function autofill(
  image: File,
  profile: Record<string, string>
): Promise<AutofillResponse> {
  const fd = new FormData();
  fd.append("image", image);
  fd.append("profile", JSON.stringify(profile));
  const res = await fetch("/api/autofill", { method: "POST", body: fd });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ---- 串流事件型別 ----
export type StreamEvent =
  | { event: "meta"; image_width: number; image_height: number; brain_model: string; eyes_model: string; mock: boolean }
  | { event: "eyes_detect"; status: "start" }
  | { event: "eyes_detect"; status: "done"; texts: DetectedText[] }
  | { event: "brain"; status: "start" }
  | { event: "brain"; status: "thinking" | "content"; text: string }
  | { event: "brain"; status: "tokens"; input_tokens: number; output_tokens: number }
  | { event: "brain"; status: "done"; fills: unknown[] }
  | { event: "locate"; status: "start"; index: number; total: number; label: string }
  | { event: "locate"; status: "item"; index: number; item: FillItem }
  | { event: "complete"; plan: FillItem[] };

/** POST 表單與個資，逐事件回呼，驅動前端動畫展示。 */
export async function autofillStream(
  image: File,
  profile: Record<string, string>,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const fd = new FormData();
  fd.append("image", image);
  fd.append("profile", JSON.stringify(profile));
  const res = await fetch("/api/autofill/stream", { method: "POST", body: fd });
  if (!res.ok || !res.body) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(5).trim()) as StreamEvent);
      } catch {
        /* 忽略解析失敗的片段 */
      }
    }
  }
}
