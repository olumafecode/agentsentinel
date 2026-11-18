"""A stand-in for Veridane's identity service, for demos and scenario runs.

When a customer signs in, the identity service issues the session token Vera passes
to the gateway (ADR-012). The scenario runner plays that part, so it holds
SESSION_TOKEN_KEY. The key is never part of Vera's own settings.
"""

import secrets
import time
from collections.abc import Callable

from banking_agent.agent import SessionContext
from sentinel_contracts import TaskType, issue_session_token


class IdentityStandIn:
    def __init__(
        self, session_key: bytes, *, clock: Callable[[], float] = time.time
    ) -> None:
        self._key = session_key
        self._clock = clock

    def sign_in(
        self,
        customer_id: str,
        task_type: TaskType | str,
        *,
        agent_id: str,
        channel: str = "web_chat",
    ) -> SessionContext:
        """Start a session for ``customer_id`` served by ``agent_id``."""
        session_id = f"SES-{secrets.randbelow(10**8):08d}"
        token = issue_session_token(
            key=self._key,
            session_id=session_id,
            customer_id=customer_id,
            agent_id=agent_id,
            task_type=task_type,
            channel=channel,
            now=self._clock(),
        )
        return SessionContext(
            session_id=session_id,
            customer_id=customer_id,
            task_type=TaskType(task_type),
            token=token,
        )
