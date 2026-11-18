# Audit trail tools image (US-19, US-20): runs migrate, verify-chain and completeness.
# Build from the repository root:
#   docker build -f services/audit-service/Dockerfile -t agentsentinel/audit-service .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first, so a code change does not reinstall them.
COPY services/audit-service/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY libs/sentinel-contracts ./libs/sentinel-contracts
COPY services/audit-service ./services/audit-service
RUN pip install --no-deps ./libs/sentinel-contracts ./services/audit-service \
    && rm -rf ./libs ./services \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin audit

USER 10001

ENTRYPOINT ["python", "-m", "sentinel_audit"]
CMD ["migrate"]
