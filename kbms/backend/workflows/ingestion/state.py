from app.workflows.base_state import KBGraphState


class ImportGraphState(KBGraphState, total=False):

    is_md_read_enabled: bool
    is_pdf_read_enabled: bool

    import_file_path: str
    output_file_dir: str
    pdf_path: str
    md_path: str

    file_title: str
    item_name: str

    md_content: str
    chunks: list

GRAPH_DEFAULT_STATE: ImportGraphState = {
    "task_id": "",
    "is_pdf_read_enabled": False,
    "is_md_read_enabled": False,
    "output_file_dir": "",
    "import_file_path": "",
    "pdf_path": "",
    "md_path": "",
    "file_title": "",
    "md_content": "",
    "chunks": [],
    "item_name": "",
}