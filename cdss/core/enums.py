from enum import StrEnum


class AgentType(StrEnum):
    INTAKE = "INTAKE"
    RESEARCH_COORDINATOR = "RESEARCH_COORDINATOR"
    SOURCE_READER = "SOURCE_READER"
    RESEARCH_AGGREGATOR = "RESEARCH_AGGREGATOR"
    TRIALS = "TRIALS"
    CROSS_INDICATION_COORD = "CROSS_INDICATION_COORD"
    KG_TRAVERSAL = "KG_TRAVERSAL"
    HYPOTHESIS = "HYPOTHESIS"
    REPORT_SYNTHESIZER = "REPORT_SYNTHESIZER"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(StrEnum):
    RUN_STARTED = "run_started"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_STARTED = "agent_started"
    SOURCE_DISCOVERED = "source_discovered"
    SOURCE_FETCHED = "source_fetched"
    LLM_CALL = "llm_call"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    PHASE_COMPLETED = "phase_completed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
