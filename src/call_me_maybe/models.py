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


class FunctionDefinition(BaseModel):
    name: str = Field(..., description="Function name")

    description: str = Field(
        ...,
        description="Function description"
    )

    parameters: list[str, FunctionParameter] = Field(
        ...,
        description="Map of parameter name → parameter definition"
    )

    returns: Dict[str, Any] = Field(
        ...,
        description="Return type definition (e.g. {'type': 'number'})"
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
    metadata: Dict[str, Any] = Field(
        ...,
        description="Must contain {'functions': [...]}"
    )


class NormalizedSchema(BaseModel):

    functions: List[FunctionDefinition] = Field(
        ...,
        description="List of available function definitions"
    )


class RawLLMOutput(BaseModel):
    token_ids: List[int]
    text: str
