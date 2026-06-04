"""功能測試：在 MOCK_MODE 下測整條 API（無需 GPU / 模型）。"""
import io
import json
import os

os.environ["MOCK_MODE"] = "1"

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _png_bytes(w=800, h=600) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["mock"] is True


def test_autofill_maps_profile_to_fields():
    profile = {"name": "王小明", "email": "ming@example.com", "phone": "0912345678"}
    r = client.post(
        "/api/autofill",
        files={"image": ("form.png", _png_bytes(), "image/png")},
        data={"profile": json.dumps(profile)},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mock"] is True
    assert body["image_width"] == 800
    values = {item["label"]: item["value"] for item in body["plan"]}
    assert values["Name"] == "王小明"
    assert values["Email"] == "ming@example.com"
    # 每個計畫項目都要有點擊座標
    for item in body["plan"]:
        assert item["point"] is not None


def test_autofill_rejects_bad_profile():
    r = client.post(
        "/api/autofill",
        files={"image": ("form.png", _png_bytes(), "image/png")},
        data={"profile": "not-json"},
    )
    assert r.status_code == 422


def test_autofill_skips_unmatched_fields():
    profile = {"email": "only@example.com"}
    r = client.post(
        "/api/autofill",
        files={"image": ("form.png", _png_bytes(), "image/png")},
        data={"profile": json.dumps(profile)},
    )
    labels = {item["label"] for item in r.json()["plan"]}
    assert labels == {"Email"}
