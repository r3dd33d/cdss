from cdss.core.enums import AgentType


class AgentRegistry:
    """Maps AgentType to agent class; populated at startup."""

    def __init__(self) -> None:
        self._map: dict[AgentType, type] = {}

    def register(self, agent_type: AgentType, cls: type) -> None:
        self._map[agent_type] = cls

    def get(self, agent_type: AgentType) -> type:
        if agent_type not in self._map:
            raise KeyError(f"No agent registered for {agent_type}")
        return self._map[agent_type]
