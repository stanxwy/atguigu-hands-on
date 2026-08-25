class ImportProcessError(Exception):

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


class StateFieldError(ImportProcessError):
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


class ConfigurationError(ImportProcessError):
    pass


class FileProcessingError(ImportProcessError):
    pass


class PdfConversionError(FileProcessingError):
    pass


class ImageProcessingError(FileProcessingError):
    pass


class DocumentSplitError(ImportProcessError):
    pass


class EmbeddingError(ImportProcessError):
    pass


class LLMError(ImportProcessError):
    pass


class StorageError(ImportProcessError):
    pass


class VectorDBError(StorageError):
    pass


class ObjectStoreError(StorageError):
    pass


class ValidationError(ImportProcessError):
    pass
