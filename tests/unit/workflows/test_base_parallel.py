from typing import Any

import pytest
from llama_index.core.workflow import StartEvent, StopEvent, Workflow, step

from lampe.core.workflows.base_parallel import BaseParallelWorkflow


class ParallelWorkflowStartEvent(StartEvent):
    """Start event that accepts inner inputs to process in parallel."""

    input: Any = None


class DummyInnerWorkflow(Workflow):
    @step
    async def run_step(self, ev: ParallelWorkflowStartEvent) -> StopEvent:
        return StopEvent(result={"echo": ev.input})


@pytest.mark.asyncio
async def test_base_parallel_workflow_steps():
    """Test that the base parallel workflow steps are working as expected."""

    workflow = BaseParallelWorkflow(inner=DummyInnerWorkflow())
    inner_events = [
        ParallelWorkflowStartEvent(input=0),
        ParallelWorkflowStartEvent(input=1),
        ParallelWorkflowStartEvent(input=2),
    ]

    result = await workflow.run(inner_events=inner_events)
    assert result == [{"echo": i} for i in range(len(inner_events))]
