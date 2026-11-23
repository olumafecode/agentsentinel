"""Fixtures for tests in every folder of the repository.

``opa_url`` starts a real OPA server with the bank's policies from policies/opa, the
way Docker Compose runs it, for tests that need the bank policy itself (US-02a). It
needs the ``opa`` command. Without it these tests are skipped on a developer's
machine; in CI, where the CI variable is set, they fail instead, so the policy is
never left untested by accident.
"""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx2
import pytest

POLICIES = Path(__file__).resolve().parent / "policies" / "opa"
OPA_START_SECONDS = 20


@pytest.fixture(scope="session")
def opa_url():
    binary = shutil.which("opa")
    if binary is None:
        message = (
            "the opa command is not installed; see policies/opa/README.md "
            "for how to install it and run the policy tests"
        )
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(message)

    port = _free_port()
    process = subprocess.Popen(
        [
            binary,
            "run",
            "--server",
            f"--addr=127.0.0.1:{port}",
            "--log-level=error",
            "--bundle",
            "--ignore=*_test.rego",
            str(POLICIES),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_ready(url, process)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(url: str, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + OPA_START_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(f"OPA stopped while starting: {process.stderr.read()}")
        try:
            if httpx2.get(f"{url}/health?bundles=true", timeout=1).status_code == 200:
                return
        except httpx2.HTTPError:
            pass
        time.sleep(0.1)
    pytest.fail(f"OPA did not become ready within {OPA_START_SECONDS} seconds")
