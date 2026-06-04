"""decord 的 arm64 stub。

decord 在 arm64 沒有官方 wheel，但它僅用於影片解碼，本專案只處理表單「圖片」，
完全用不到。LocateAnything-3B 的程式碼已能容忍 decord 缺席，唯獨 transformers 的
靜態 import 檢查 (check_imports) 要求此套件可被 import，故提供此空殼。
若日後需要影片功能，請在 x86_64 環境改裝真正的 decord。
"""
__version__ = "0.0.0-stub"


def __getattr__(name):  # 任何屬性存取都明確報錯，避免誤用
    raise NotImplementedError(
        f"decord.{name} 不可用：本環境為 arm64 stub，僅支援圖片，不支援影片。"
    )
