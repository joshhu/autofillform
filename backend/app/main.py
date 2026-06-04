"""FastAPI 入口：API + 內建前端網頁（單一埠對外）。"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from app.config import settings
from app.loader import load_image
from app.pipeline import run_autofill, run_autofill_stream
from app.schemas import AutofillResponse

app = FastAPI(title="AutoFillForm", description="兩小模型協作自動填表系統", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_profile(profile: str) -> dict[str, str]:
    try:
        data = json.loads(profile)
        if not isinstance(data, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=422, detail="profile 必須是 JSON 物件")
    return {str(k): str(v) for k, v in data.items()}


async def _read(image: UploadFile) -> Image.Image:
    raw = await image.read()
    try:
        return load_image(raw, image.filename or "", image.content_type or "")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"無法讀取檔案（支援圖片 / PDF）：{e}")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "mock": settings.MOCK_MODE,
        "brain_model": settings.BRAIN_MODEL,
        "eyes_model": settings.LOCATE_MODEL_PATH,
    }


@app.post("/api/autofill", response_model=AutofillResponse)
async def autofill(
    image: UploadFile = File(..., description="表單截圖或 PDF"),
    profile: str = Form(..., description="使用者個資的 JSON 字串"),
) -> AutofillResponse:
    return run_autofill(await _read(image), _parse_profile(profile))


@app.post("/api/autofill/stream")
async def autofill_stream(
    image: UploadFile = File(..., description="表單截圖或 PDF"),
    profile: str = Form(..., description="使用者個資的 JSON 字串"),
) -> StreamingResponse:
    """以 Server-Sent Events 逐步驟串流整個填表過程，供前端動畫展示。"""
    profile_data = _parse_profile(profile)
    img = await _read(image)

    def gen():
        for ev in run_autofill_stream(img, profile_data):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# 內建前端：若已 build（frontend/dist 存在）則掛載，跨機器只需開這一個埠。
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="web")
