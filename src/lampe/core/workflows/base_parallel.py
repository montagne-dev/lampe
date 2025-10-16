import logging
import os
from typing import Any

from llama_index.core.workflow import Context, Event, StartEvent, StopEvent, Workflow, step
from pydantic import BaseModel

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

PARALLEL_WORKFLOW_MAX_WORKERS = int(os.getenv("PARALLEL_WORKFLOW_MAX_WORKERS", 32))


class FailedInnerEvent(BaseModel):
    """Model to store information about a failed inner event."""

    event: Event
    error: str


class ParallelStartEvent(StartEvent):
    """Start event that accepts inner inputs to process in parallel."""

    inner_events: list[Event]


class ProcessInnerInputEvent(Event):
    """Event to process a single inner input."""

    inner_event: Event


class InnerInputResultEvent(Event):
    """Event containing the result of processing an inner input."""

    result: Any


class BaseParallelWorkflow(Workflow):
    """Base workflow that processes multiple inner inputs in parallel.

    Uses multiple workers to process inner inputs concurrently using an inner workflow.
    The inner workflow must accept a single 'input' parameter and return a result that can
    be collected into a list.

    Example:
    >>> inner_workflow = Workflow()
    >>> workflow = BaseParallelWorkflow(inner=inner_workflow)
    >>> result = await workflow.run(inner_events=[1, 2, 3])
    >>> print(result)
    """

    def __init__(self, *args, inner: Workflow, **kwargs):
        super().__init__(*args, **kwargs)
        self.inner = inner

    @step
    async def start(self, ctx: Context, ev: ParallelStartEvent) -> ProcessInnerInputEvent | None:
        await ctx.store.set("num_to_collect", len(ev.inner_events))
        logger.debug(f"Starting parallel workflow with {len(ev.inner_events)} inner inputs")
        for inner_event in ev.inner_events:
            ctx.send_event(ProcessInnerInputEvent(inner_event=inner_event))

    @step(num_workers=PARALLEL_WORKFLOW_MAX_WORKERS)
    async def process_inner_event(self, ev: ProcessInnerInputEvent) -> InnerInputResultEvent:
        inner_name = self.inner.__class__.__name__
        inner_event_name = type(ev.inner_event).__name__
        logger.debug(f"Processing inner workflow ({inner_name}) for event type: {inner_event_name}")
        try:
            result = await self.inner.run(start_event=ev.inner_event)
        except Exception as e:
            logger.exception(f"Error processing inner workflow: {e}")
            return InnerInputResultEvent(result=FailedInnerEvent(event=ev.inner_event, error=str(e)))

        logger.debug(
            f"Processed inner workflow ({inner_name}) for event type: {inner_event_name}, "
            f"result type: {type(result).__name__}"
        )
        return InnerInputResultEvent(result=result)

    @step
    async def combine_results(self, ctx: Context, ev: InnerInputResultEvent) -> StopEvent | None:
        num_to_collect = await ctx.store.get("num_to_collect")
        logger.debug(f"Combining results ({num_to_collect})")
        results = ctx.collect_events(ev, [InnerInputResultEvent] * num_to_collect)
        if results is None:
            return None

        logger.debug("Collected all results")
        combined_results = [event.result for event in results]
        return StopEvent(result=combined_results)
