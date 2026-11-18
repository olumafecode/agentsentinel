# Demo bank API image (US-16.4). Build from the repository root:
#   docker build -f apps/demo-bank-api/Dockerfile -t agentsentinel/demo-bank-api .
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first, so a code change does not reinstall them.
COPY apps/demo-bank-api/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY libs/sentinel-contracts ./libs/sentinel-contracts
COPY apps/demo-bank-api ./apps/demo-bank-api
RUN pip install --no-deps ./libs/sentinel-contracts ./apps/demo-bank-api \
    && rm -rf ./libs ./apps \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin bank

USER 10001
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/healthz', timeout=2)"]

CMD ["python", "-m", "uvicorn", "demo_bank_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
