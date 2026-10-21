FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENV SEC_USER_AGENT=""
CMD ["uv", "run", "pytest", "-q", "-m", "not slow"]
