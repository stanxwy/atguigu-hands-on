import os
import re
from collections import deque
from pathlib import Path

from app.domain.ports.llm import LLMPort
from app.domain.ports.object_store import ObjectStore
from app.utils.api_throttle import apply_api_rate_limit
from app.utils.backup_utils import backup_file
from app.workflows.ingestion.base import BaseNode
from app.workflows.ingestion.exceptions import (
    FileProcessingError,
    StateFieldError,
)
from app.workflows.ingestion.state import ImportGraphState

IMAGE_CONTEXT_LENGTH = 100

class NodeMDImg(BaseNode):

    name: str = "node_md_img"

    def __init__(self, 
                 llm_service: LLMPort,
                 object_store: ObjectStore):
        super().__init__()
        self._llm_service = llm_service
        self._object_store = object_store

    def _validate_input_state(self, state: ImportGraphState) -> tuple[str, Path, Path]:
        md_content = state["md_content"]
        if not md_content:
            raise StateFieldError(field_name='md_content', message="md_content cannot be empty", expected_type=str)

        md_path = state.get("md_path")
        if not md_path:
            raise StateFieldError(field_name='md_path', message="md_path is required", expected_type=str)

        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            raise FileProcessingError(message=f"MD file {md_path_obj.name} does not exist")

        images_dir_obj = md_path_obj.parent / "images"

        return md_content, md_path_obj, images_dir_obj

    def _collect_ref_images(self, md_content: str, images_dir_obj: Path) -> list[tuple[str, str, tuple[str, str]]]:
        referenced_images = []
        for image_file in os.listdir(images_dir_obj):
            self.logger.info(f"Checking image file: {image_file}")

            file_ext = os.path.splitext(image_file)[1].lower()
            if file_ext not in self.config.image_extensions:
                self.logger.info(f"Image extension not supported, skip：{image_file}")
                continue

            if (images_dir_obj / image_file).stat().st_size < self.config.min_image_size:
                self.logger.info(f"Image too small, skip：{image_file}")
                continue
            
            context = self._extract_image_context(md_content, image_file)
            if not context:
                self.logger.info(f"Image not referenced in MD, skip: {image_file}")
                continue

            img_local_path = str(images_dir_obj / image_file)
            referenced_images.append((image_file, img_local_path, context))

        self.logger.info(f"Images to be processed: {len(referenced_images)}")
        return referenced_images
    
    def _extract_image_context(self, md_content: str, image_file: str, context_len: int = IMAGE_CONTEXT_LENGTH) -> tuple[str, str]:
        # ![alt text](images/file.extension)
        pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_file) + r".*?\)")
        match = pattern.search(md_content)
        if not match:
            return None

        start, end = match.span()
        self.logger.info(f"Image {image_file} position in MD: {start}-{end}")
        pre_text = md_content[max(0, start - context_len):start]
        post_text = md_content[end:min(len(md_content), end + context_len)]
        return pre_text, post_text

    def _generate_image_captions(self, doc_stem: str, target_images: list[tuple[str, str, tuple[str, str]]]) -> dict[str, str]:
        captions = {}
        request_deque = deque()

        count = 0
        for img_file, img_local_path, context in target_images:
            apply_api_rate_limit(request_deque)
            captions[img_file] = self._llm_service.generate_image_caption(img_local_path, doc_stem, context)
            count = count + 1
            self.logger.info(f"{count} image caption generated")
        return captions
    
    def _upload_images_batch(self, doc_stem: str, target_images: list[tuple]) -> dict[str, str]:
        upload_dir = doc_stem.replace(" ", "")
        self._object_store.clean_img_dir(upload_dir) # idempotent operation

        urls = {}
        for img_file, img_local_path, _ in target_images:
            urls[img_file] = self._object_store.upload_img(img_local_path, f"{upload_dir}/{img_file}")
            self.logger.info(f"Image {img_file} uploaded to {urls[img_file]}")
        self.logger.info(f"{len(target_images)} images uploaded to Object Store")
        return urls

    def _replace_img_alt_and_url(self, md_content: str, captions: dict[str, str], urls: dict[str, str]) -> str:
        for img_file, caption in captions.items():
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(img_file) + r".*?\)")
            md_content = pattern.sub(lambda _: f"![{caption}]({urls.get(img_file)})", md_content)

        self.logger.info(f"Image caption and url updated in MD, total processed: {len(captions)}")
        return md_content

    def _backup_new_md_file(self, md_path_obj: str, md_content: str) -> str:
        new_md_file = os.path.splitext(md_path_obj)[0] + "_new.md"
        backup_file(new_md_file, md_content)
        return new_md_file

    def process(self, state: ImportGraphState) -> ImportGraphState:

        md_content, md_path_obj, images_dir_obj = self._validate_input_state(state)
        if not images_dir_obj.exists():
            self.logger.info("Directory 'images/' not found, skip image processing")
            return {}

        referenced_images = self._collect_ref_images(md_content, images_dir_obj)
        if not referenced_images:
            self.logger.info("No referenced images found, skip image processing")
            return {}

        captions = self._generate_image_captions(md_path_obj.stem, referenced_images)

        urls = self._upload_images_batch(md_path_obj.stem, referenced_images)

        new_md_content = self._replace_img_alt_and_url(md_content, captions, urls)

        new_md_file = self._backup_new_md_file(md_path_obj, new_md_content)

        return {
            "md_path": new_md_file,
            "md_content": new_md_content
        }