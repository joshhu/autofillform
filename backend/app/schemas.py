"""API 與內部流程共用的資料結構。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """像素座標的邊界框。"""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class DetectedText(BaseModel):
    """眼睛模型偵測到的一段文字（通常是欄位標籤）。"""
    text: str
    bbox: BBox


class FillItem(BaseModel):
    """大腦規劃出的單一填寫動作，已附上眼睛定位到的精準座標。"""
    label: str = Field(..., description="欄位標籤，例如 Email、姓名")
    value: str = Field(..., description="要填入的值")
    target_phrase: str = Field(..., description="給眼睛定位用的自然語言描述")
    bbox: BBox | None = Field(None, description="眼睛回傳的輸入框座標")
    point: tuple[float, float] | None = Field(None, description="點擊用的中心點座標")
    reason: str | None = Field(None, description="大腦的對應理由")


class AutofillResponse(BaseModel):
    image_width: int
    image_height: int
    detected_texts: list[DetectedText]
    plan: list[FillItem]
    brain_model: str
    eyes_model: str
    mock: bool = False
