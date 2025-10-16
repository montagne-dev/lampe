import pytest

from lampe.template.template_workflow import TemplateWorkflow


@pytest.mark.asyncio
async def test_template_workflow():
    workflow = TemplateWorkflow()
    result = await workflow.run()
    assert "Hello," in result
