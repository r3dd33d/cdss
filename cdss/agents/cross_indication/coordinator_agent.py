from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.core.models.hypothesis import OffLabelHypothesis
from cdss.core.models.patient import PatientProfile
from cdss.integrations.clinical_trials import EVIDENCE_LABELS
from cdss.knowledge.graph import loader
from cdss.knowledge.graph.queries import find_drugs_for_gene
from cdss.observability.run_context import RunContext


class CrossIndicationTask(AgentTask):
    profile: PatientProfile


class CrossIndicationCoordinator(BaseAgent):
    """Routes to KG traversal when available; skips gracefully otherwise."""

    def __init__(self, **_) -> None:
        pass

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: CrossIndicationTask = task  # type: ignore[assignment]
        if not loader.KG_AVAILABLE:
            return AgentResult(run_id=ctx.run_id, data=[], validation_flags=["KG_SKIPPED"])

        hypotheses = []
        for biomarker in t.profile.biomarkers:
            candidates = find_drugs_for_gene(biomarker.gene)
            for c in candidates:
                # Assign evidence level 1 (in-vitro) as a conservative default.
                level = 1
                hypotheses.append(OffLabelHypothesis(
                    drug_name=c["drug"],
                    approved_indication=c["approved_indication"],
                    shared_mechanism=c["shared_pathway"],
                    evidence_level=level,
                    evidence_label=EVIDENCE_LABELS.get(level, "Unknown"),
                    citation="PrimeKG graph traversal",
                ))
        return AgentResult(run_id=ctx.run_id, data=hypotheses)
