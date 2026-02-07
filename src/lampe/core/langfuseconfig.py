import logging
import os
from functools import wraps
from typing import Any, Callable

from httpx import ConnectError
from langfuse import Langfuse
from langfuse.api import UnauthorizedError
from llama_index_instrumentation import get_dispatcher
from openinference.instrumentation.config import TraceConfig
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.maskingconfig import is_masking_enabled

DEFAULT_AUTH_VALUE = "optional"
logger = logging.getLogger(LAMPE_LOGGER_NAME)
langfuse_client = None
dispatcher = None


def trace_with_function_name(func: Callable) -> Callable:
    """
    Decorator that automatically updates the current trace with function name and metadata.

    The decorated function should have a 'metadata' parameter to pass additional metadata
    to the trace.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        # Extract metadata from kwargs, defaulting to empty dict if not provided
        metadata = kwargs.get("metadata", {})

        # Create tags list with function name
        tags = [func.__name__]

        # Update current trace with metadata and tags
        update_current_trace(metadata=metadata, tags=tags)

        # Call the original function
        return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        # Extract metadata from kwargs, defaulting to empty dict if not provided
        metadata = kwargs.get("metadata", {})

        # Create tags list with function name
        tags = [func.__name__]

        # Update current trace with metadata and tags
        update_current_trace(metadata=metadata, tags=tags)

        # Call the original function
        return func(*args, **kwargs)

    # Return appropriate wrapper based on whether function is async
    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def trace_span(func: Callable) -> Callable:
    """Decorator that add any non auto-instrumented function to the langfuse trace."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if dispatcher:
            return dispatcher.span(func)(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    return wrapper


def is_telemetry_enabled():
    return os.getenv("TELEMETRY_ENABLED", "false").lower() == "true"


def init_langfuse():
    telemetry_enabled = is_telemetry_enabled()
    try:
        # NOTE: We are forced to add default values for secret and public key otherwise auth check will fail
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", DEFAULT_AUTH_VALUE),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", DEFAULT_AUTH_VALUE),
            host=os.getenv("LANGFUSE_HOST"),
            tracing_enabled=telemetry_enabled,
        )
        if telemetry_enabled and langfuse.auth_check():
            logger.info(
                "Langfuse client is authenticated and ready! Setting up LlamaIndex instrumentation with masking."
            )
            if is_masking_enabled():
                logger.info("Masking is enabled sensitive data will be masked in telemetry.")
                config = TraceConfig(
                    hide_llm_invocation_parameters=True,
                    hide_inputs=True,
                    hide_outputs=True,
                    hide_input_messages=True,
                    hide_output_messages=True,
                    hide_input_images=True,
                    hide_input_text=True,
                    hide_output_text=True,
                    hide_prompts=True,
                )
                LlamaIndexInstrumentor().instrument(config=config)
                global dispatcher
                dispatcher = get_dispatcher(__name__)
            else:
                logger.warning(
                    "Security Notice: Telemetry masking is DISABLED - sensitive data will be visible in telemetry"
                )
                LlamaIndexInstrumentor().instrument()
        else:
            raise ValueError("Authentication failed. Please check your credentials and host.")

        global langfuse_client
        langfuse_client = langfuse
    except (UnauthorizedError, ValueError, AttributeError) as e:
        error_type = "Authentication" if isinstance(e, UnauthorizedError) else "General"
        if telemetry_enabled:
            logger.warning(f"{error_type} error: {e}. No instrumentation will be done.")
        return None
    except ConnectError as e:
        if telemetry_enabled:
            logger.warning(f"Connection error: {e}. No instrumentation will be done.")
        return None
    except Exception as e:
        if telemetry_enabled:
            logger.exception(f"Unexpected error: {e}. No instrumentation will be done.")
        return None


def update_current_trace(metadata: dict | None = None, tags: list[str] | None = None):
    global langfuse_client
    if langfuse_client and is_telemetry_enabled():
        langfuse_client.update_current_trace(metadata=metadata, tags=tags)
