"""把上傳的檔案（圖片或 PDF）載入成 PIL Image。"""
from __future__ import annotations

import base64
import io

from PIL import Image


def load_image(raw: bytes, filename: str = "", content_type: str = "") -> Image.Image:
    """支援一般圖片與 PDF（取第一頁，以 150 DPI 轉點陣圖）。"""
    is_pdf = (
        content_type == "application/pdf"
        or filename.lower().endswith(".pdf")
        or raw[:5] == b"%PDF-"
    )
    if is_pdf:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=raw, filetype="pdf")
        if doc.page_count == 0:
            raise ValueError("PDF 沒有頁面")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()
        return img
    return Image.open(io.BytesIO(raw)).convert("RGB")


def to_png_data_url(image: Image.Image) -> str:
    """轉成可直接放進 <img src> 的 data URL，確保前端顯示的就是模型看到的像素。"""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"
