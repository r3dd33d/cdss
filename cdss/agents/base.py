from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from cdss.observability.run_context import RunContext


class AgentTask(BaseModel):
    """Minimal input slice passed to one agent run."""
    model_config = {"arbitrary_types_allowed": True}


class AgentResult(BaseModel):
    """Output of one agent run plus observability metadata."""
    run_id: str
    data: Any = None
    validation_flags: list[str] = []
    model_config = {"arbitrary_types_allowed": True}


class BaseAgent(ABC):
    @abstractmethod
    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult: ...
