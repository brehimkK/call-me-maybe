class CallMeMaybeError(Exception):
    """Base exception for all application-specific errors."""
    pass


class InputParseError(CallMeMaybeError):
    """Raised when input data cannot be parsed correctly."""
    pass


class SchemaError(CallMeMaybeError):
    """Raised when a schema is invalid or malformed."""
    pass


class ValidationError(CallMeMaybeError):
    """Raised when data validation fails."""
    pass


class LLMError(CallMeMaybeError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMInternalError(LLMError):
    pass


class OutputParseError(CallMeMaybeError):
    """Raised when the LLM output cannot be parsed."""
    pass
