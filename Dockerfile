# Author: Bradley R. Kinnard
# Multi-stage build for SNRE

FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


FROM base AS production
WORKDIR /app
COPY snre/ snre/
COPY agents/ agents/
COPY core/ core/
COPY interface/ interface/
COPY config/ config/
COPY main.py pyproject.toml setup.py ./

RUN mkdir -p data/refactor_logs/sessions data/snapshots logs

RUN groupadd -r snre && useradd -r -g snre snre && \
    chown -R snre:snre /app
USER snre

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "snre", "api", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS dev
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"
RUN mkdir -p data/refactor_logs/sessions data/snapshots logs
CMD ["pytest", "tests/", "-v", "--tb=short"]
