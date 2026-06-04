"""兩模型協作的編排：眼睛 → 大腦 → 眼睛。

1. 眼睛(LocateAnything) 對截圖做文字偵測 → 表單文字地圖
2. 大腦(Qwen3.6) 讀地圖 + 個資 → 填寫計畫(含定位描述)
3. 眼睛 對每個描述做 GUI 定位 → 精準座標
4. 組合成最終填寫計畫
"""
from __future__ import annotations

from collections.abc import Iterator

from PIL import Image

from app.config import settings
from app.schemas import AutofillResponse, BBox, DetectedText, FillItem


def _mock_run(image: Image.Image, profile: dict[str, str]) -> AutofillResponse:
    """無 GPU / 測試用：依個資產生可預期的假計畫。"""
    w, h = image.size
    texts = [
        DetectedText(text="Name", bbox=BBox(x1=0.1 * w, y1=0.10 * h, x2=0.3 * w, y2=0.15 * h)),
        DetectedText(text="Email", bbox=BBox(x1=0.1 * w, y1=0.25 * h, x2=0.3 * w, y2=0.30 * h)),
        DetectedText(text="Phone", bbox=BBox(x1=0.1 * w, y1=0.40 * h, x2=0.3 * w, y2=0.45 * h)),
    ]
    label_map = {"Name": ["name", "姓名"], "Email": ["email", "電子郵件"],
                 "Phone": ["phone", "電話", "手機"]}
    plan: list[FillItem] = []
    for t in texts:
        value = ""
        for key in label_map.get(t.text, []):
            if key in profile:
                value = profile[key]
                break
        if not value:
            continue
        box = BBox(x1=0.35 * w, y1=t.bbox.y1, x2=0.7 * w, y2=t.bbox.y2)
        plan.append(FillItem(
            label=t.text, value=value,
            target_phrase=f"the input box for {t.text}",
            bbox=box, point=box.center, reason="mock 對應",
        ))
    return AutofillResponse(
        image_width=w, image_height=h, detected_texts=texts, plan=plan,
        brain_model=settings.BRAIN_MODEL, eyes_model=settings.LOCATE_MODEL_PATH, mock=True,
    )


def run_autofill(image: Image.Image, profile: dict[str, str]) -> AutofillResponse:
    if settings.MOCK_MODE:
        return _mock_run(image, profile)

    # 延遲匯入，避免無 GPU 環境匯入 torch 失敗
    from app.models.brain import BrainClient
    from app.models.locate import LocateAnythingWorker

    eyes = LocateAnythingWorker.get()
    brain = BrainClient()
    w, h = image.size

    # 1) 眼睛：偵測表單文字
    texts = eyes.detect_texts(image)

    # 2) 大腦：規劃填寫
    fills = brain.plan_fill(profile, texts)

    # 3) 眼睛：逐欄精準定位
    plan: list[FillItem] = []
    for f in fills:
        phrase = f.get("target_phrase") or f"the input box for {f.get('label', '')}"
        bbox, point = eyes.ground(image, phrase)
        plan.append(FillItem(
            label=f.get("label", ""), value=str(f.get("value", "")),
            target_phrase=phrase, bbox=bbox, point=point, reason=f.get("reason"),
        ))

    return AutofillResponse(
        image_width=w, image_height=h, detected_texts=texts, plan=plan,
        brain_model=settings.BRAIN_MODEL, eyes_model=settings.LOCATE_MODEL_PATH, mock=False,
    )


def run_autofill_stream(image: Image.Image, profile: dict[str, str]) -> Iterator[dict]:
    """同樣的流程，但逐步驟 yield 事件，供前端動畫展示整個過程。

    事件型別 (event)：
      meta          → 影像尺寸與模型資訊
      eyes_detect   → 眼睛偵測文字 (start / done+texts)
      brain         → 大腦推理 (start / done+fills)
      locate        → 逐欄定位 (start / item)
      complete      → 完整填寫計畫
    """
    from app.loader import to_png_data_url

    w, h = image.size
    yield {"event": "meta", "image_width": w, "image_height": h,
           "image_data_url": to_png_data_url(image),
           "brain_model": settings.BRAIN_MODEL, "eyes_model": settings.LOCATE_MODEL_PATH,
           "mock": settings.MOCK_MODE}

    if settings.MOCK_MODE:
        result = _mock_run(image, profile)
        yield {"event": "eyes_detect", "status": "start"}
        yield {"event": "eyes_detect", "status": "done",
               "texts": [t.model_dump() for t in result.detected_texts]}
        yield {"event": "brain", "status": "start"}
        # 模擬思考串流
        think = "分析偵測到的欄位並對應使用者資料…\n"
        for it in result.plan:
            think += f"- {it.label} → {it.value}\n"
        for word in think.split(" "):
            yield {"event": "brain", "status": "thinking", "text": word + " "}
        yield {"event": "brain", "status": "tokens", "input_tokens": 1234, "output_tokens": 256}
        yield {"event": "brain", "status": "done",
               "fills": [{"label": it.label, "value": it.value,
                          "target_phrase": it.target_phrase, "reason": it.reason}
                         for it in result.plan]}
        for i, it in enumerate(result.plan):
            yield {"event": "locate", "status": "start", "index": i,
                   "total": len(result.plan), "label": it.label}
            yield {"event": "locate", "status": "item", "index": i, "item": it.model_dump()}
        yield {"event": "complete", "plan": [it.model_dump() for it in result.plan]}
        return

    from app.models.brain import BrainClient
    from app.models.locate import LocateAnythingWorker

    eyes = LocateAnythingWorker.get()
    brain = BrainClient()

    yield {"event": "eyes_detect", "status": "start"}
    texts = eyes.detect_texts(image)
    yield {"event": "eyes_detect", "status": "done",
           "texts": [t.model_dump() for t in texts]}

    yield {"event": "brain", "status": "start"}
    fills: list[dict] = []
    for ev in brain.plan_fill_stream(profile, texts):
        if ev["type"] == "thinking":
            yield {"event": "brain", "status": "thinking", "text": ev["text"]}
        elif ev["type"] == "content":
            yield {"event": "brain", "status": "content", "text": ev["text"]}
        elif ev["type"] == "result":
            fills = ev["fills"]
            yield {"event": "brain", "status": "tokens",
                   "input_tokens": ev["input_tokens"], "output_tokens": ev["output_tokens"]}
    yield {"event": "brain", "status": "done", "fills": fills}

    plan: list[FillItem] = []
    for i, f in enumerate(fills):
        label = f.get("label", "")
        phrase = f.get("target_phrase") or f"the input box for {label}"
        yield {"event": "locate", "status": "start", "index": i,
               "total": len(fills), "label": label}
        bbox, point = eyes.ground(image, phrase)
        item = FillItem(label=label, value=str(f.get("value", "")),
                        target_phrase=phrase, bbox=bbox, point=point, reason=f.get("reason"))
        plan.append(item)
        yield {"event": "locate", "status": "item", "index": i, "item": item.model_dump()}

    yield {"event": "complete", "plan": [it.model_dump() for it in plan]}
