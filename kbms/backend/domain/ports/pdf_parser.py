from abc import ABC, abstractmethod
from pathlib import Path


class PDFParser(ABC):

    @abstractmethod
    def get_upload_url(self, file_name: str) -> str: ...

    @abstractmethod
    def upload_file(self, file_path: str, upload_url: str) -> str: ...

    @abstractmethod
    def poll_task_status(self, batch_id: str) -> str: ...

    @abstractmethod
    def download_zip(self, zip_url: str, output_dir: str, pdf_stem: str) -> str: ...

    @abstractmethod
    def extract_processed_doc(self, zip_file_path: str, output_dir: str, pdf_stem: str) -> Path: ...