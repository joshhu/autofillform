"""集中管理設定，全部可由環境變數覆寫。"""
from __future__ import annotations

import os


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


class Settings:
    # 大腦：Qwen3.6 35B A3B，透過 Ollama 提供
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    BRAIN_MODEL: str = os.getenv("BRAIN_MODEL", "qwen3.6:35b")

    # 眼睛：NVIDIA LocateAnything-3B（VLM），以 Transformers 載入
    LOCATE_MODEL_PATH: str = os.getenv("LOCATE_MODEL_PATH", "nvidia/LocateAnything-3B")
    LOCATE_DEVICE: str = os.getenv("LOCATE_DEVICE", "cuda")
    LOCATE_DTYPE: str = os.getenv("LOCATE_DTYPE", "bfloat16")
    LOCATE_GEN_MODE: str = os.getenv("LOCATE_GEN_MODE", "hybrid")
    LOCATE_MAX_TOKENS: int = int(os.getenv("LOCATE_MAX_TOKENS", "4096"))

    # MOCK_MODE=1 時不載入任何模型，回傳假資料（無 GPU 也能跑測試 / 前端開發）
    MOCK_MODE: bool = _bool("MOCK_MODE", False)

    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:9080"
    ).split(",")


settings = Settings()
