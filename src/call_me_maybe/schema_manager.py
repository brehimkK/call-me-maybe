from pydantic import BaseModel, Field
from typing import Dict, Any, List


class FunctionParameter(BaseModel):
    """
    Represents the type constraints for a single function argument.
    Used to ensure the LLM provides the correct data type (e.g., number, string).
    """
    type: str = Field(..., description="The expected data type, e.g., 'number' or 'string'")


class FunctionDefinition(BaseModel):
    """
    Groups the metadata of a tool together.
    This serves as the 'manual' that describes what each function does and requires.
    """
    name: str = Field(..., description="The unique name of the function")
    description: str = Field(..., description="Natural language explanation of the tool")
    parameters: Dict[str, FunctionParameter] = Field(..., description="Map of parameter names to their types")
    returns: Dict[str, str] = Field(..., description="The return type of the function")


class FunctionCallResult(BaseModel):
    """
    The final output format required by the subject.
    Ensures the output contains exactly the prompt, name, and parameters.
    """
    prompt: str = Field(..., description="The original natural-language request")
    name: str = Field(..., description="The name of the function to call")
    parameters: Dict[str, Any] = Field(..., description="The arguments extracted by the LLM")


class SchemaManager:
    """
    The main controller for your schemas.
    It loads raw data and provides helper methods for the Decoder.
    """
    def __init__(self, functions_list: List[Dict[str, Any]]):
        """
        Initializes the manager by validating a list of raw dictionaries 
        into Pydantic FunctionDefinition objects.
        """
        # This handles the requirement to handle malformed inputs gracefully
        self.available_functions: List[FunctionDefinition] = [
            FunctionDefinition(**fn) for fn in functions_list
        ]

    def get_function_names(self) -> List[str]:
        """Returns a list of all valid function names for the decoder to enforce."""
        return [fn.name for fn in self.available_functions]

    def get_params_for_function(self, func_name: str) -> Dict[str, str]:
        """
        Retrieves the parameter names and their expected types 
        for a specific function.
        """
        for fn in self.available_functions:
            if fn.name == func_name:
                return {name: p.type for name, p in fn.parameters.items()}
        return {}
