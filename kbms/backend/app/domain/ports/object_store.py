from abc import ABC, abstractmethod


class ObjectStore(ABC):

    @abstractmethod
    def clean_dir(self, dir_path: str) -> None: ...

    @abstractmethod
    def upload(self, local_path: str, object_name: str, content_type: str | None = None) -> str | None: ...

    @abstractmethod
    def clean_img_dir(self, doc_stem: str) -> None: ...

    @abstractmethod
    def upload_img(self, local_path: str, object_name: str, content_type: str | None = None) -> str | None: ...