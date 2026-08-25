from pathlib import Path

from app.workflows.ingestion.base import BaseNode
from app.workflows.ingestion.exceptions import (
    FileProcessingError,
    StateFieldError,
    ValidationError,
)
from app.workflows.ingestion.state import ImportGraphState


class NodeEntry(BaseNode):

    name: str = "node_entry"

    def _validate_input_state(self, state):
        
        import_file_path = state.get("import_file_path")
        if not import_file_path:
            raise StateFieldError(field_name='import_file_path', expected_type=str)

        import_file_path_obj = Path(import_file_path)
        if not import_file_path_obj.exists():
            raise FileProcessingError(message=f"File {import_file_path_obj.name} does not exist")
        
        file_stem = import_file_path_obj.stem

        if import_file_path_obj.suffix == ".pdf":
            return {
                "is_pdf_read_enabled": True,
                "pdf_path": import_file_path,
                "file_title": file_stem
            }
        elif import_file_path_obj.suffix == ".md":
            return {
                "is_md_read_enabled": True,
                "md_path": import_file_path,
                "file_title": file_stem
            }
        else:
            raise ValidationError(message=f"File extension {import_file_path_obj.suffix} not supported")

    def process(self, state: ImportGraphState) -> ImportGraphState:
        return self._validate_input_state(state)