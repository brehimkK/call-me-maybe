from .models import FunctionDefinition
from typing import List, Dict, Any, Optional


class SchemaManager:
    """
    Central registry for function schemas.
    Validates raw definitions and exposes query helpers for decoding.
    """

    def __init__(self, functions_list: List[Dict[str, Any]]):
        """
        Converts raw function dictionaries into validated FunctionDefinition objects.
        Skips or raises on invalid entries depending on strict policy.
        """

        self.available_functions: List[FunctionDefinition] = []

        for fn in functions_list:
            try:
                self.available_functions.append(FunctionDefinition(**fn))
            except Exception:
                continue

        self._function_map: Dict[str, FunctionDefinition] = {
            fn.name: fn for fn in self.available_functions
        }

    def get_function_names(self) -> List[str]:
        """Returns all valid function names."""
        return list(self._function_map.keys())

    def get_params_for_function(self, func_name: str) -> Dict[str, str]:
        """
        Returns parameter name → type mapping for a function.
        """

        fn = self._function_map.get(func_name)
        if not fn:
            return {}

        return {
            param.name: param.type
            for param in fn.parameters
        }

    def get_function(self, func_name: str) -> Optional[FunctionDefinition]:
        """Returns full function definition if exists."""
        return self._function_map.get(func_name)
