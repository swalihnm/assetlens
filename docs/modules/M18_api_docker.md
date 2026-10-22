# M18 API, Docker and CI

**Method.** FastAPI (`/benchmarks`, `/forecast`, `POST /mandate/price`, `/allocation`, `/growth-case`) over a read-only warehouse connection with input validation and JSON-safe output; Dockerfile (core dependencies only, 1.38 GB) and docker-compose for API plus Streamlit; GitHub Actions workflow runs lint, tests and a Docker build; cross-platform `pipeline` runner and a `refresh` job that rebuilds everything when Goldman files its next 10-Q.

**Outputs.** `src/assetlens/api/app.py`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `pipeline.py`, `refresh.py`.

**Results and validation.** Containers built and queried (API returned live warehouse data, Streamlit health 200). CI green on GitHub. A clean clone rebuilt the whole project and passed 60/60 tests.

**Limitations.** CI skips tests that need the SEC cache; the full suite runs locally.
