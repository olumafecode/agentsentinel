# OPA image for AgentSentinel (US-20), serving the bank's policy bundle (US-02a).
# Build from the repository root:
#   docker build -f policies/opa/Dockerfile -t agentsentinel/opa .
#
# The official OPA images cannot run an HTTP health check: the plain ones have no
# shell, and the busybox in the -debug ones leaves out wget. So this image puts OPA's
# statically linked binary on the official busybox image, which has wget. The policies
# are copied in, so the image also runs where a folder cannot be mounted (Railway,
# Render, Kubernetes). OPA serves them as a bundle, so every decision carries the
# bundle's revision from .manifest, and the health check waits for the bundle.
FROM openpolicyagent/opa:1.22.4-static AS opa

FROM busybox:1.37.0-musl

COPY --from=opa /opa /usr/local/bin/opa
COPY policies/opa /policies

USER 1000:1000
EXPOSE 8181

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8181/health?bundles=true"]

ENTRYPOINT ["/usr/local/bin/opa"]
CMD ["run", "--server", "--addr=0.0.0.0:8181", "--log-level=error", "--bundle", "--ignore=*_test.rego", "/policies"]
