from dataclasses import dataclass, field


@dataclass(frozen=True)
class RunContext:
    run_id: str
    parent_id: str | None = None
    depth: int = 0

    def child(self, child_run_id: str) -> "RunContext":
        return RunContext(run_id=child_run_id, parent_id=self.run_id, depth=self.depth + 1)
