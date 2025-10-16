import asyncio

from llama_index.core.workflow import StartEvent, StopEvent, Workflow, step


class TemplateWorkflow(Workflow):
    """A template workflow that demonstrates basic workflow structure.

    This workflow is responsible for:
    - Demonstrating the basic workflow pattern
    - Showing how to handle events
    - Providing a template for new workflows
    """

    @step
    async def template_step(self, ev: StartEvent) -> StopEvent:
        return StopEvent(result=f"Hello, from {__name__}!")


async def run_workflow(timeout: int | None = None):
    workflow = TemplateWorkflow(timeout=timeout, verbose=False)
    result = await workflow.run()
    return result


def main():
    result = asyncio.run(run_workflow())
    print(result)


if __name__ == "__main__":
    main()
