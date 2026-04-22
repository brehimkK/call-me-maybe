from pydantic import BaseModel, Field
from typing import Any, List, Optional, Literal, Dict


class FunctionParameter(BaseModel):
    """
    Represents a single function argument definition.
    Used to enforce type safety and validation for LLM function calls.
    """

    name: str = Field(..., description="Name of the parameter")

    type: Literal[
        "string", "integer", "array", "number", "boolean", "object"] = Field(
        ..., description="Expected data type of the parameter"
    )

    required: bool = Field(
        default=True,
        description="Whether this parameter is required"
    )

    description: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of the parameter"
    )

    default: Optional[Any] = Field(
        default=None,
        description="Default value used if parameter is not required"
    )

    enum: Optional[List[Any]] = Field(
        default=None,
        description="Allowed set of values for this parameter"
    )


class FunctionDefinition(BaseModel):
    """
    Defines a complete tool/function contract.
    Acts as the LLM-facing specification for function calling.
    """

    name: str = Field(..., description="Unique name of the function")

    description: str = Field(
        ...,
        description="Natural language explanation of what the function does"
    )

    parameters: List[FunctionParameter] = Field(
        default_factory=list,
        description="Ordered list of function parameters"
    )

    strict: bool = Field(
        default=True,
        description="If true, disallows unknown arguments"
    )

    returns: Optional[str] = Field(
        default=None,
        description="Description or type of the return value"
    )


class FunctionCallResult(BaseModel):
    """
    Final validated function call result after LLM parsing and validation.
    """

    prompt: str = Field(
        ...,
        description="Original user request in natural language"
    )

    function_name: str = Field(
        ...,
        description="Name of the function to be executed"
    )

    arguments: Dict[str, Any] = Field(
        ...,
        description="Validated arguments extracted from LLM output"
    )

    success: bool = Field(
        default=True,
        description="Whether the function call is valid and executable"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if validation or execution failed"
    )

    raw_output: Optional[Any] = Field(
        default=None,
        description="Original raw LLM response (for debugging/traceability)"
    )


class ParsedInput(BaseModel):
    """
    Output of the parsing stage before schema resolution.
    """

    raw_text: str = Field(
        ...,
        description="Original user input"
    )

    intent: str = Field(
        ...,
        description="Detected intent label"
    )

    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted structured values from user input"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parser diagnostics and extra context"
    )


class NormalizedSchema(BaseModel):
    """
    Canonical schema used by the LLM decoding and validation pipeline.

    This is a deterministic, serializable representation of all available
    function definitions with enforced ordering rules.
    """

    schema_version: str = Field(
        default="1.0",
        description="Version of the schema format"
    )

    functions: List[FunctionDefinition] = Field(
        ...,
        description="List of available function definitions"
    )

    field_order: List[str] = Field(
        default_factory=lambda: [
            "name", "description", "parameters", "strict", "returns"],
        description="Canonical field order used for "
        "deterministic serialization"
    )


class RawLLMOutput(BaseModel):
    """
    Represents the raw, unprocessed response returned by an LLM provider.
    This includes the source (provider), the specific model used, and
    the raw content generated. It is used for debugging, logging,
    and downstream parsing.
    """

    provider: str = Field(
        ...,
        description="The LLM service provider that generated the response "
        "(e.g., 'openai', 'anthropic')"
    )

    model: str = Field(
        ...,
        description="The name of the model used to generate the response"
        " (e.g., 'gpt-5', 'claude-3')"
    )

    content: str = Field(
        ...,
        description="The raw text output returned by "
        "the LLM before any parsing or validation"
    )
