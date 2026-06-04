"""大腦：Qwen3.6 35B A3B（透過 Ollama）。

純文字推理：吃進「使用者個資」+「眼睛轉出的表單文字地圖」，推理每個欄位該填什麼，
並產出給眼睛定位用的自然語言描述。它不看圖，所以用純文字 MoE 跑得又快又省。
"""
from __future__ import annotations

import json

import httpx

from app.config import settings
from app.schemas import DetectedText

_SYSTEM = (
    "你是自動填表系統的大腦。你會收到（1）使用者的個人資料，"
    "（2）由視覺模型偵測出的表單畫面文字清單（含每段文字的位置）。"
    "請判斷這張表單有哪些「需要填寫的欄位」，並把使用者資料對應到正確欄位。"
    "只輸出 JSON，格式為物件並含 key `fills`，其值為陣列，每個元素："
    '{"label": 欄位標籤, "value": 要填入的值, '
    '"target_phrase": 給定位模型的英文描述(例如 "the input box for Email"), '
    '"reason": 簡短理由}。'
    "找不到對應資料的欄位請略過，不要捏造。只輸出 JSON，不要其他文字。"
)


class BrainClient:
    def __init__(self) -> None:
        self.host = settings.OLLAMA_HOST.rstrip("/")
        self.model = settings.BRAIN_MODEL

    def plan_fill(self, profile: dict[str, str], texts: list[DetectedText]) -> list[dict]:
        text_map = [
            {"text": t.text, "x": round(t.bbox.center[0]), "y": round(t.bbox.center[1])}
            for t in texts
        ]
        user_msg = (
            f"使用者個人資料：\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n\n"
            f"表單畫面偵測到的文字（含中心座標）：\n"
            f"{json.dumps(text_map, ensure_ascii=False, indent=2)}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0.2},
        }
        with httpx.Client(timeout=180) as client:
            r = client.post(f"{self.host}/api/chat", json=payload)
            r.raise_for_status()
            content = r.json()["message"]["content"]
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        fills = data.get("fills", data if isinstance(data, list) else [])
        return [f for f in fills if isinstance(f, dict) and f.get("value")]
