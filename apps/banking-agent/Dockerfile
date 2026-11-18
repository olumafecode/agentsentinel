# Vera image (US-17): runs the scripted scenarios against the gateway.
# Build from the repository root:
#   docker build -f apps/banking-agent/Dockerfile -t agentsentinel/banking-agent .
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first, so a code change does not reinstall them.
COPY apps/banking-agent/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY libs/sentinel-contracts ./libs/sentinel-contracts
COPY apps/banking-agent ./apps/banking-agent
RUN pip install --no-deps ./libs/sentinel-contracts ./apps/banking-agent \
    && rm -rf ./libs ./apps \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin vera

USER 10001

ENTRYPOINT ["python", "-m", "banking_agent"]
CMD ["run"]
