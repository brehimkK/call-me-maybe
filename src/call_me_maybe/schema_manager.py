from .models import FunctionDefinition
from typing import List, Dict, Any, Optional
from .errors import SchemaError, ValidationError
import pydantic


class SchemaManager:
    """
    Central registry for function schemas.
    Validates raw definitions and exposes query helpers for decoding.
    """

    def __init__(self, functions_list: List[Dict[str, Any]]) -> None:
        """
        Converts raw function dictionaries
          into validated FunctionDefinition objects.
        Skips or raises on invalid entries depending on strict policy.
        """

        self.available_functions: List[FunctionDefinition] = []
        self._function_names: set[str] = set()

        for fn in functions_list:
            try:

                func = FunctionDefinition(**fn)
            except pydantic.ValidationError as e:
                raise SchemaError(
                    f"Invalid function definition for "
                    f"{fn.get('name', 'unknown')}: {e}"
                ) from e

            if func.name in self._function_names:
                raise ValidationError(f"{func.name} is already on the list")

            self._function_names.add(func.name)
            self.available_functions.append(func)

        if not self.available_functions:
            raise SchemaError("No valid function definitions provided")

    def get_function_names(self) -> List[str]:
        return sorted(self._function_names)

    def get_params_for_function(self, func_name: str) -> dict[str, str]:
        """
        Returns parameter name → type mapping for a function.
        """

        fn = next((
            f for f in self.available_functions if f.name == func_name), None)
        if not fn:
            return {}

        return {
            param.name: param.type
            for param in fn.parameters}

    def get_function(self, func_name: str) -> Optional[FunctionDefinition]:
        """Returns full function definition if exists."""
        return next(
            (func for func in self.available_functions
             if func.name == func_name),
            None
        )
