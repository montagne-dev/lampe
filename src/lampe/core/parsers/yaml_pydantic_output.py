import logging
from typing import Generic

import yaml
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.types import Model

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.parsers.utils import extract_md_code_block

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


class YAMLParsingError(Exception):
    """Raised when YAML parsing or validation fails."""

    pass


class YAMLPydanticOutputParser(PydanticOutputParser[Model], Generic[Model]):
    """
    A parser that extracts and validates YAML content using Pydantic models.

    Parameters
    ----------
    output_cls
        Pydantic output class used for validation
    excluded_schema_keys_from_format
        Schema keys to exclude from format string, by default None
    pydantic_format_tmpl
        Template for format string, by default PYDANTIC_FORMAT_TMPL

    Notes
    -----
    This parser extracts YAML content from markdown code blocks, validates the structure
    using a Pydantic model, and returns the validated data. It first looks for YAML-specific
    code blocks, then falls back to any code block if needed.
    """

    @property
    def format_string(self) -> str:
        """Get the format string that instructs the LLM how to output YAML.

        This method will provide a format string that includes the Pydantic model's JSON schema
        converted to a YAML example, helping the LLM understand the expected output structure.

        Returns
        -------
        :
            Format string with YAML schema example

        Raises
        ------
        NotImplementedError
            The method is not yet implemented
        """
        raise NotImplementedError(
            "YAML schema formatting is not yet implemented. Future versions will provide "
            "proper YAML schema guidance based on the Pydantic model."
        )

    def parse(self, text: str) -> Model:
        """
        Extract, parse and validate YAML content using the configured Pydantic model.

        Parameters
        ----------
        text
            Raw text containing YAML content in markdown code blocks

        Returns
        -------
        :
            Validated data matching the Pydantic model structure

        Raises
        ------
        YAMLParsingError
            If no valid YAML content is found in the text or if the YAML parsing fails due to syntax errors
        ValidationError
            If the data does not match the Pydantic model schema
        """
        if not text:
            raise YAMLParsingError("No text provided")

        yaml_block = extract_md_code_block(text, "yaml")
        if not yaml_block:
            logger.warning("No YAML block found, attempting to parse generic code block")
            yaml_block = extract_md_code_block(text)
        if not yaml_block:
            yaml_block = text
        try:
            data = yaml.safe_load(yaml_block)
        except yaml.YAMLError as e:
            raise YAMLParsingError(f"Invalid YAML syntax: {e}") from e

        return self.output_cls.model_validate(data)
