class QueryProcessError(Exception):

    def __init__(self, message: str, node_name: str = "", cause: Exception = None):
        self.node_name = node_name
        self.cause = cause
        super().__init__(message)

    def __str__(self):
        parts = []
        if self.node_name:
            parts.append(f"[{self.node_name}]")
        parts.append(super().__str__())
        if self.cause:
            parts.append(f"(Cause: {self.cause})")
        return " ".join(parts)


class StateFieldError(QueryProcessError):
    def __init__(
        self,
        node_name: str = "",
        field_name: str = "",
        expected_type: type = None,
        message: str = "",
        cause: Exception = None,
    ):
        self.field_name = field_name
        self.expected_type = expected_type
        if not message:
            message = f"State field '{field_name}' missing or invalid"
            if expected_type:
                message += f"，expected type: {expected_type.__name__}"
        super().__init__(message, node_name=node_name, cause=cause)


class ConfigurationError(QueryProcessError):
    pass


class EmbeddingError(QueryProcessError):
    pass

class LLMError(QueryProcessError):
    pass

class StorageError(QueryProcessError):
    pass

class VectorDBError(StorageError):
    pass

class ValidationError(QueryProcessError):
    pass
