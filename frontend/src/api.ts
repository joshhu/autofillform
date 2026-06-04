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
