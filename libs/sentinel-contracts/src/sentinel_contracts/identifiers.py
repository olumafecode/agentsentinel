"""Identifier and value formats shared by every AgentSentinel service.

The patterns are the same as in data/synthetic/models.py. The test
tests/test_contracts_match_schema.py fails if the two ever disagree.
"""

from typing import Annotated

from pydantic import StringConstraints

CustomerId = Annotated[str, StringConstraints(pattern=r"^CUS-\d{6}$")]
AccountId = Annotated[str, StringConstraints(pattern=r"^ACC-\d{8}$")]
TransactionId = Annotated[str, StringConstraints(pattern=r"^TXN-\d{10}$")]
DisputeId = Annotated[str, StringConstraints(pattern=r"^DSP-\d{6}$")]
AgentId = Annotated[str, StringConstraints(pattern=r"^AGT-\d{3}$")]
SessionId = Annotated[str, StringConstraints(pattern=r"^SES-\d{8}$")]
ApprovalId = Annotated[str, StringConstraints(pattern=r"^APR-\d{6}$")]
CorrelationId = Annotated[
    str,
    StringConstraints(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    ),
]
SemVer = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
EventId = Annotated[str, StringConstraints(pattern=r"^EVT-\d{6}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ToolName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{2,40}$")]
ArgumentName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
