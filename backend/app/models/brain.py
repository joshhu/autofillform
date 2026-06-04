"""大腦：Qwen3.6 35B A3B（透過 Ollama）。

純文字推理：吃進「使用者個資」+「眼睛轉出的表單文字地圖」，推理每個欄位該填什麼，
並產出給眼睛定位用的自然語言描述。它不看圖，所以用純文字 MoE 跑得又快又省。

提供兩種介面：
  plan_fill        一次回傳結果（給非串流流程用）
  plan_fill_stream 串流回傳「思考過程 + token 數 + 最終結果」（給即時展示用）
"""
from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from app.config import settings
from app.schemas import DetectedText

_SYSTEM = (
    "你是自動填表系統的大腦。你會收到（1）使用者的個人資料，"
    "（2）由視覺模型偵測出的表單畫面文字清單（含每段文字的位置）。"
    "請逐步思考：判斷這張表單有哪些「需要填寫的欄位」，把使用者資料對應到正確欄位，"
    "再用一個 JSON 物件輸出最終結果。JSON 含 key `fills`，其值為陣列，每個元素："
    '{"label": 欄位標籤, "value": 要填入的值, '
    '"target_phrase": 給定位模型的英文描述(例如 "the input box for Email"), '
    '"reason": 簡短理由}。'
    "找不到對應資料的欄位請略過，不要捏造。最終只輸出該 JSON 物件。"
)


def _build_messages(profile: dict[str, str], texts: list[DetectedText]) -> list[dict]:
    text_map = [
        {"text": t.text, "x": round(t.bbox.center[0]), "y": round(t.bbox.center[1])}
        for t in texts
    ]
    user_msg = (
        f"使用者個人資料：\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n\n"
        f"表單畫面偵測到的文字（含中心座標）：\n"
        f"{json.dumps(text_map, ensure_ascii=False, indent=2)}"
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_msg},
    ]


def _extract_fills(content: str) -> list[dict]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 容錯：從文字中抓出第一個 JSON 物件
        start, depth = content.find("{"), 0
        if start < 0:
            return []
        for i in range(start, len(content)):
            depth += {"{": 1, "}": -1}.get(content[i], 0)
            if depth == 0:
                try:
                    data = json.loads(content[start : i + 1])
                    break
                except json.JSONDecodeError:
                    return []
        else:
            return []
    fills = data.get("fills", data if isinstance(data, list) else [])
    return [f for f in fills if isinstance(f, dict) and f.get("value")]


class BrainClient:
    def __init__(self) -> None:
        self.host = settings.OLLAMA_HOST.rstrip("/")
        self.model = settings.BRAIN_MODEL

    def plan_fill(self, profile: dict[str, str], texts: list[DetectedText]) -> list[dict]:
        payload = {
            "model": self.model,
            "messages": _build_messages(profile, texts),
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0.2},
        }
        with httpx.Client(timeout=180) as client:
            r = client.post(f"{self.host}/api/chat", json=payload)
            r.raise_for_status()
            content = r.json()["message"]["content"]
        return _extract_fills(content)

    def plan_fill_stream(
        self, profile: dict[str, str], texts: list[DetectedText]
    ) -> Iterator[dict]:
        """串流大腦推理。yield：
          {"type":"thinking","text":...}  思考片段
          {"type":"content","text":...}   答案片段
          {"type":"result","fills":[...],"input_tokens":N,"output_tokens":M}
        """
        payload = {
            "model": self.model,
            "messages": _build_messages(profile, texts),
            "stream": True,
            "think": True,
            "options": {"temperature": 0.2},
        }
        content_buf: list[str] = []
        in_tok = out_tok = 0
        with httpx.Client(timeout=300) as client:
            with client.stream("POST", f"{self.host}/api/chat", json=payload) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    msg = chunk.get("message", {})
                    if msg.get("thinking"):
                        yield {"type": "thinking", "text": msg["thinking"]}
                    if msg.get("content"):
                        content_buf.append(msg["content"])
                        yield {"type": "content", "text": msg["content"]}
                    if chunk.get("done"):
                        in_tok = chunk.get("prompt_eval_count", 0)
                        out_tok = chunk.get("eval_count", 0)
        yield {
            "type": "result",
            "fills": _extract_fills("".join(content_buf)),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }
