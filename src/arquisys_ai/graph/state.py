from __future__ import annotations

from typing import TypedDict

from arquisys_ai.core.models import AnalystResult, ArchitectResult


class WorkflowState(TypedDict):
    user_request: str
    analysis: AnalystResult | None
    architecture: ArchitectResult | None
    status: str
