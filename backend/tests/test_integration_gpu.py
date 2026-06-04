"""整合測試：真實兩模型協作（需 GPU + Ollama + 已下載模型）。

預設跳過；要跑請設 RUN_GPU_TESTS=1 並確保：
  - Ollama 已啟動且有 qwen3.6:35b
  - 已下載 nvidia/LocateAnything-3B 與 GPU 依賴
"""
import os

import pytest
from PIL import Image

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_GPU_TESTS") != "1", reason="需 GPU/模型，設 RUN_GPU_TESTS=1 才跑"
)


def test_real_pipeline_locates_and_fills():
    os.environ["MOCK_MODE"] = "0"
    from app.pipeline import run_autofill

    img = Image.open(
        os.path.join(os.path.dirname(__file__), "..", "..", "samples", "form.png")
    ).convert("RGB")
    profile = {
        "name": "王小明", "email": "ming@example.com",
        "phone": "0912345678", "address": "台北市信義路100號",
    }
    r = run_autofill(img, profile)
    assert not r.mock
    labels = {it.label.lower() for it in r.plan}
    assert any("email" in la for la in labels)
    # 每個計畫項目都要定位到座標
    for it in r.plan:
        assert it.point is not None
        assert 0 <= it.point[0] <= r.image_width
        assert 0 <= it.point[1] <= r.image_height
