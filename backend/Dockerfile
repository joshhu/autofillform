# 眼睛模型需 GPU。Base 請對應你的 CUDA 版本（DGX Spark 為 CUDA 13 / arm64）。
FROM nvcr.io/nvidia/pytorch:25.03-py3

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY vendor ./vendor
COPY app ./app
# 安裝執行期依賴 + GPU 依賴；decord 以 arm64 stub 取代（僅圖片用途）
RUN uv pip install --system -e ".[gpu]" && \
    uv pip install --system -e vendor/decord-stub

ENV MOCK_MODE=0
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
