class CallMeMaybeError(Exception):
    """Base exception for all application-specific errors."""
    pass


class InputParseError(CallMeMaybeError):
    """Raised when input data cannot be parsed correctly."""
    pass


class SchemaError(CallMeMaybeError):
    """Raised when a schema is invalid or malformed."""
    pass


class LLMAdapterError(CallMeMaybeError):
    """Raised when there is an error communicating with the LLM."""
    pass


class LLMTimeoutError(LLMAdapterError):
    """Raised when the LLM request times out."""
    pass


class OutputParseError(CallMeMaybeError):
    """Raised when the LLM output cannot be parsed."""
    pass


class ValidationError(CallMeMaybeError):
    """Raised when data validation fails."""
    pass

