"""眼睛：NVIDIA LocateAnything-3B 包裝。

負責「看」：對表單截圖做文字偵測（拿到所有標籤與位置），以及 GUI 元素定位
（給一句描述，回傳該輸入框的精準座標）。大腦不看圖，只靠這裡轉出的文字與座標。
"""
from __future__ import annotations

import re
import threading

from PIL import Image

from app.config import settings
from app.schemas import BBox, DetectedText

# LocateAnything 輸出正規化到 [0, 1000] 的座標 token
_BOX_RE = re.compile(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>")
_POINT_RE = re.compile(r"<box><(\d+)><(\d+)></box>")
# 偵測文字時，模型以 <ref>標籤</ref><box>...</box> 的形式列出
_REF_BOX_RE = re.compile(
    r"<ref>(.*?)</ref>\s*<box><(\d+)><(\d+)><(\d+)><(\d+)></box>"
)


def parse_boxes(answer: str, w: int, h: int) -> list[BBox]:
    """把 [0,1000] 正規化框換算回像素。"""
    out: list[BBox] = []
    for m in _BOX_RE.finditer(answer):
        x1, y1, x2, y2 = (int(g) for g in m.groups())
        out.append(BBox(x1=x1 / 1000 * w, y1=y1 / 1000 * h,
                        x2=x2 / 1000 * w, y2=y2 / 1000 * h))
    return out


def parse_point(answer: str, w: int, h: int) -> tuple[float, float] | None:
    m = _POINT_RE.search(answer)
    if not m:
        return None
    x, y = int(m.group(1)), int(m.group(2))
    return (x / 1000 * w, y / 1000 * h)


def parse_text_boxes(answer: str, w: int, h: int) -> list[DetectedText]:
    """解析「<ref>標籤</ref><box>...</box>」的偵測結果。"""
    out: list[DetectedText] = []
    for m in _REF_BOX_RE.finditer(answer):
        text = m.group(1).strip(" -•\t")
        x1, y1, x2, y2 = (int(m.group(i)) for i in range(2, 6))
        if not text:
            continue
        out.append(DetectedText(
            text=text,
            bbox=BBox(x1=x1 / 1000 * w, y1=y1 / 1000 * h,
                      x2=x2 / 1000 * w, y2=y2 / 1000 * h),
        ))
    return out


class LocateAnythingWorker:
    """單例，第一次使用時才載入模型（lazy load）。"""

    _instance: "LocateAnythingWorker | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        import torch
        from transformers import AutoModel, AutoProcessor, AutoTokenizer

        dtype = getattr(torch, settings.LOCATE_DTYPE)
        path = settings.LOCATE_MODEL_PATH
        self.tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
        self.processor = AutoProcessor.from_pretrained(path, trust_remote_code=True)
        self.model = (
            AutoModel.from_pretrained(path, torch_dtype=dtype, trust_remote_code=True)
            .to(settings.LOCATE_DEVICE)
            .eval()
        )
        self._torch = torch
        self.dtype = dtype
        self.device = settings.LOCATE_DEVICE

    @classmethod
    def get(cls) -> "LocateAnythingWorker":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ask(self, image: Image.Image, question: str) -> str:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": question},
        ]}]
        text = self.processor.py_apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        images, videos = self.processor.process_vision_info(messages)
        inputs = self.processor(
            text=[text], images=images, videos=videos, return_tensors="pt"
        ).to(self.device)
        with self._torch.no_grad():
            resp = self.model.generate(
                pixel_values=inputs["pixel_values"].to(self.dtype),
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                image_grid_hws=inputs.get("image_grid_hws", None),
                tokenizer=self.tokenizer,
                max_new_tokens=settings.LOCATE_MAX_TOKENS,
                generation_mode=settings.LOCATE_GEN_MODE,
                temperature=0.3,
                do_sample=True,
                top_p=0.9,
                use_cache=True,
            )
        return resp[0] if isinstance(resp, tuple) else resp

    def detect_texts(self, image: Image.Image) -> list[DetectedText]:
        """偵測畫面上所有文字（含座標），作為大腦的「表單地圖」。"""
        w, h = image.size
        answer = self._ask(image, "Detect all the text in box format.")
        return parse_text_boxes(answer, w, h)

    def ground(self, image: Image.Image, phrase: str) -> tuple[BBox | None, tuple[float, float] | None]:
        """GUI 定位：給一句描述，回傳該輸入框的框與中心點。"""
        w, h = image.size
        box_ans = self._ask(image, f"Locate the region that matches: {phrase}.")
        boxes = parse_boxes(box_ans, w, h)
        bbox = boxes[0] if boxes else None
        pt_ans = self._ask(image, f"Point to: {phrase}.")
        point = parse_point(pt_ans, w, h)
        if point is None and bbox is not None:
            point = bbox.center
        return bbox, point
