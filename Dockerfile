FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 UV_CONCURRENT_DOWNLOADS=2 UV_CONCURRENT_INSTALLS=1 PYTHONPATH=/app/src
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev
COPY app ./app
COPY config ./config
COPY docs ./docs
# data/ (DuckDB warehouse, raw cache) and outputs/ are mounted at run time - never baked into the image
VOLUME ["/app/data", "/app/outputs"]
EXPOSE 8000 8501
CMD ["uv", "run", "--no-sync", "uvicorn", "assetlens.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
