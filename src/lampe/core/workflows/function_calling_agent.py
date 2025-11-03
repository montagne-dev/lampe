import logging
from typing import Any, List

from llama_index.core.llms import ChatMessage
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool, ToolOutput, ToolSelection
from llama_index.core.workflow import Context, Event, StartEvent, Workflow, step
from llama_index.llms.litellm import LiteLLM

from lampe.core.llmconfig import MODELS
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME


class InputEvent(Event):
    input: list[ChatMessage]


class ToolCallEvent(Event):
    tool_calls: list[ToolSelection]


class FunctionOutputEvent(Event):
    output: ToolOutput


class AgentCompleteEvent(Event):
    output: str | None
    sources: list[ToolOutput]


class FunctionCallingAgent(Workflow):
    def __init__(
        self,
        *args: Any,
        llm: FunctionCallingLLM | None = None,
        tools: List[FunctionTool] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)
        self.logger.debug("Initializing FunctionCallingAgent with args: %s, kwargs: %s", args, kwargs)
        super().__init__(*args, **kwargs)
        self.tools = tools or []
        self.llm = llm or LiteLLM(
            model=MODELS.GPT_5_NANO_2025_08_07, temperature=1.0, reasoning_effort="low"
        )  # Default to OpenAI LLM
        assert self.llm.metadata.is_function_calling_model
        # Store system prompt
        self.system_prompt = system_prompt

    @step
    async def prepare_chat_history(self, ctx: Context, ev: StartEvent) -> InputEvent:
        # Clear sources
        await ctx.store.set("sources", [])

        # Check if memory is setup
        memory = await ctx.store.get("memory", default=None)
        if not memory:
            memory = ChatMemoryBuffer.from_defaults(llm=self.llm)

        # Add system prompt to memory if it exists
        if self.system_prompt:
            system_msg = ChatMessage(role="system", content=self.system_prompt)
            memory.put(system_msg)

        # Get user input
        user_input = ev.input
        user_msg = ChatMessage(role="user", content=user_input)
        memory.put(user_msg)

        # Get chat history
        chat_history = memory.get()

        # Update context
        await ctx.store.set("memory", memory)

        return InputEvent(input=chat_history)

    @step
    async def handle_llm_input(self, ctx: Context, ev: InputEvent) -> ToolCallEvent | AgentCompleteEvent:
        chat_history = ev.input

        # stream the response
        response = await self.llm.achat_with_tools(self.tools, chat_history=chat_history)

        # save the final response, which should have all content
        memory = await ctx.store.get("memory")
        memory.put(response.message)
        await ctx.store.set("memory", memory)
        tool_calls = self.llm.get_tool_calls_from_response(response, error_on_no_tool_call=False)
        if not tool_calls:
            sources = await ctx.store.get("sources", default=[])
            return AgentCompleteEvent(output=response.message.content, sources=sources)
        else:
            return ToolCallEvent(tool_calls=tool_calls)

    @step
    async def handle_tool_calls(self, ctx: Context, ev: ToolCallEvent) -> InputEvent:
        tool_calls = ev.tool_calls
        tools_by_name = {tool.metadata.get_name(): tool for tool in self.tools}
        tool_msgs = []
        sources = await ctx.store.get("sources", default=[])
        for tool_call in tool_calls:
            tool = tools_by_name.get(tool_call.tool_name)
            additional_kwargs = {
                "tool_call_id": tool_call.tool_id,
                "name": tool.metadata.get_name() if tool else tool_call.tool_name,
            }
            if not tool:
                tool_msgs.append(
                    ChatMessage(
                        role="tool",
                        content=f"Tool {tool_call.tool_name} does not exist",
                        additional_kwargs=additional_kwargs,
                    )
                )
                continue
            try:
                self.logger.debug(f"--------------{tool_call.tool_name}------------------")
                self.logger.debug(f"kwargs {tool_call.tool_kwargs}")
                tool_output = tool(**tool_call.tool_kwargs)
                self.logger.debug(f"Tool output:\n {tool_output}")
                self.logger.debug("--------------------------------")
                sources.append(tool_output)
                tool_msgs.append(
                    ChatMessage(role="tool", content=tool_output.content, additional_kwargs=additional_kwargs)
                )
            except Exception as e:
                tool_msgs.append(
                    ChatMessage(
                        role="tool", content=f"Encountered error in tool call: {e}", additional_kwargs=additional_kwargs
                    )
                )
        memory = await ctx.store.get("memory")
        for msg in tool_msgs:
            memory.put(msg)
        await ctx.store.set("sources", sources)
        await ctx.store.set("memory", memory)
        chat_history = memory.get()
        return InputEvent(input=chat_history)
