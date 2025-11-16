import logging
from typing import Any

from llama_index.core.llms import ChatMessage
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool, ToolOutput, ToolSelection
from llama_index.core.workflow import Context, Event, Workflow, step
from llama_index.llms.litellm import LiteLLM
from pydantic import BaseModel
from workflows.events import StopEvent

from lampe.core.llmconfig import MODELS
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME


class UserInputEvent(Event):
    input: str


class InputEvent(Event):
    input: list[ChatMessage]


class ToolCallEvent(Event):
    tool_calls: list[ToolSelection]


class FunctionOutputEvent(Event):
    output: ToolOutput


class ToolSource(BaseModel):
    tool_name: str
    tool_kwargs: dict[str, Any]
    tool_output: ToolOutput | str


class AgentCompleteEvent(Event):
    output: str | None
    sources: list[ToolSource]


class FunctionCallingAgent(Workflow):
    def __init__(
        self,
        *args: Any,
        llm: FunctionCallingLLM | None = None,
        tools: list[FunctionTool] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)
        self.logger.info("Initializing FunctionCallingAgent with args: %s, kwargs: %s", args, kwargs)
        super().__init__(*args, **kwargs)
        self.tools = tools or []
        self.llm = llm or LiteLLM(
            model=MODELS.GPT_5_NANO_2025_08_07, temperature=1.0, reasoning_effort="low"
        )  # Default to OpenAI LLM
        assert self.llm.metadata.is_function_calling_model
        # Store system prompt
        self.system_prompt = system_prompt

    def update_tools(self, partial_params: dict[str, Any] | None = None) -> None:
        """
        Update tool partial parameters safely: only include params present in fn_schema.model_fields,
        and merge with any existing partial_params dictionary.
        """
        for tool in self.tools:
            if (
                not hasattr(tool, "partial_params")
                or not hasattr(tool, "metadata")
                or getattr(tool.metadata, "fn_schema", None) is None
            ):
                continue

            final_params = dict(getattr(tool, "partial_params", {}) or {})
            model_fields = getattr(tool.metadata.fn_schema, "model_fields", {})

            if partial_params:
                for k, v in partial_params.items():
                    if k in model_fields:
                        final_params[k] = v

            # Only update the tool's partial_params if there is at least one valid param
            if final_params:
                tool.partial_params = final_params

    @step
    async def prepare_chat_history(self, ctx: Context, ev: UserInputEvent) -> InputEvent:
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
    async def handle_agent_completion(self, ctx: Context, ev: AgentCompleteEvent) -> StopEvent:
        return StopEvent(result=ev)

    @step
    async def handle_tool_calls(self, ctx: Context, ev: ToolCallEvent) -> InputEvent:
        tool_calls = ev.tool_calls
        tools_by_name = {tool.metadata.get_name(): tool for tool in self.tools}
        tool_msgs = []
        sources = await ctx.store.get("sources", default=[])
        for tool_call in tool_calls:
            tool_output = ""
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
                for key, value in tool_call.tool_kwargs.items():
                    if key in tool.partial_params:
                        self.logger.info(f"Tool {tool_call.tool_name} partial param {key} value {value}")

                self.logger.info(f"-------------- {tool_call.tool_name} ------------------")
                self.logger.info(f"kwargs {tool_call.tool_kwargs}")
                tool_output = tool(**tool_call.tool_kwargs)
                self.logger.info(f"Tool output:\n {tool_output}")
                self.logger.info("--------------------------------")

                tool_msgs.append(
                    ChatMessage(role="tool", content=tool_output.content, additional_kwargs=additional_kwargs)
                )
            except Exception as e:
                tool_output = f"Encountered error in tool call: \n{e}"
                tool_msgs.append(ChatMessage(role="tool", content=tool_output, additional_kwargs=additional_kwargs))
            finally:
                sources.append(
                    ToolSource(
                        tool_name=tool_call.tool_name, tool_kwargs=tool_call.tool_kwargs, tool_output=tool_output
                    )
                )
        memory = await ctx.store.get("memory")
        for msg in tool_msgs:
            memory.put(msg)
        await ctx.store.set("sources", sources)
        await ctx.store.set("memory", memory)
        chat_history = memory.get()
        return InputEvent(input=chat_history)
