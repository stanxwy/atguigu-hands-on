import logging
import shutil
import time
import zipfile
from pathlib import Path

import requests

from app.domain.ports.pdf_parser import PDFParser
from app.infra.config.settings import Settings
from app.workflows.ingestion.exceptions import PdfConversionError

POST_TIMEOUT = 30       # request for upload url
PUT_TIMEOUT = (30, 60)  # upload file
GET_TIMEOUT = 10        # poll task status, download zip

POLL_TIMEOUT = 600
POLL_INTERVAL = 3

logger = logging.getLogger(__name__)

class MineruService(PDFParser):
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._file_url = f"{settings.mineru_base_url}/file-urls/batch"
        self._poll_url = f"{settings.mineru_base_url}/extract-results/batch"

    def _build_header(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._settings.mineru_api_token}",
            "Accept": "*/*"
        }

    def _build_req_data(self, file_name: str) -> dict:
        return {
            "files": [ { "name": file_name } ],
            "model_version": "vlm"
        }


    def get_upload_url(self, file_name: str) -> str:
        header = self._build_header()
        data = self._build_req_data(file_name)

        logger.info(f"get_upload_url start: {self._file_url}, data: {data}")
        response = requests.post(self._file_url, headers=header, json=data, timeout=POST_TIMEOUT)
        if response.status_code != 200:
            raise PdfConversionError(message=f"get_upload_url http error: {response}")

        result = response.json()
        logger.info(f"get_upload_url response: {result}")
        if result.get("code") != 0:
            raise PdfConversionError(f"get_upload_url error: {result}")

        upload_url = result["data"]["file_urls"][0]
        batch_id = result["data"]["batch_id"]
        logger.info(f"get_upload_url success, batch_id: {batch_id}, upload_url: {upload_url}")
        return upload_url, batch_id

        
    def upload_file(self, file_path: str, upload_url: str) -> str:
        with open(Path(file_path), "rb") as f:
            logger.info(f"Start to upload file, signed_url: {upload_url}")
            res_upload = requests.put(upload_url, data=f, timeout=PUT_TIMEOUT)
            if res_upload.status_code != 200:
                raise PdfConversionError(f"upload_doc http error: {res_upload}")
            logger.info("upload_doc success")


    def poll_task_status(self, batch_id: str) -> str:
        poll_url = f"{self._poll_url}/{batch_id}"
        header = self._build_header()

        start_time = time.time() 
        logger.info(f"Start to poll task status, max timeout: {POLL_TIMEOUT}s, poll_url: {poll_url}")

        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > POLL_TIMEOUT:
                raise TimeoutError(f"{batch_id} poll_task_status timeout after {POLL_TIMEOUT}s")

            try:
                logger.info(f"start to poll, url: {poll_url}")
                poll_result = requests.get(url=poll_url, headers=header, timeout=GET_TIMEOUT)
            except Exception as e:
                logger.warning(f"{batch_id} poll_task_status error, will retry after {POLL_INTERVAL}s: {str(e)}")
                time.sleep(POLL_INTERVAL)
                continue

            if poll_result.status_code != 200:
                raise PdfConversionError(f"{batch_id} poll_task_status http error: {poll_result}")
            poll_data = poll_result.json()
            logger.info(f"poll_task_status success: {poll_data}")
            if poll_data["code"] != 0:
                raise PdfConversionError(f"{batch_id} poll_task_status error: {poll_data}")

            tasks = poll_data["data"]["extract_result"]
            task = tasks[0]
            data_state = task["state"]
            # state: done | waiting-file | pending | running | converting | failed
            if data_state == "done":
                logger.info(f"{batch_id} task done, total time: {int(elapsed_time)}s")

                full_zip_url = task["full_zip_url"]
                logger.info(f"{batch_id} full_zip_url: {full_zip_url}")
                return full_zip_url

            elif data_state == "failed":
                err_msg = task.get("err_msg", "MinerU Task Unknown Error")
                raise PdfConversionError(f"{batch_id} task failed: {err_msg}")

            else:
                logger.info(f"{batch_id} task status: {data_state}, total time: {int(elapsed_time)}s")
                time.sleep(POLL_INTERVAL)


    def download_zip(self, zip_url: str, output_dir: str, pdf_stem: str) -> str:
        output_dir_obj = Path(output_dir)
        if not output_dir_obj.exists():
            logger.info(f"Output directory does not exist. Creating: {output_dir_obj.absolute()}")
            output_dir_obj.mkdir(parents=True, exist_ok=True)

        logger.info(f"Start to download zip, url: {zip_url}")
        response = requests.get(zip_url, timeout=GET_TIMEOUT)

        if response.status_code != 200:
            raise RuntimeError(f"download_zip http error: {response}")

        zip_file_path = output_dir_obj / f"{pdf_stem}_result.zip"
        with open(zip_file_path, "wb") as f:
            f.write(response.content)
        logger.info(f"download_zip success, save path: {zip_file_path}")
        return str(zip_file_path.absolute())
    

    def extract_processed_doc(self, zip_file_path: str, output_dir: str, pdf_stem: str) -> Path:
        # idempotent operation
        extract_target_dir = Path(output_dir) / pdf_stem
        if extract_target_dir.exists():
            shutil.rmtree(extract_target_dir)
            logger.info(f"removed existing extract dir: {extract_target_dir}")
        extract_target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(Path(zip_file_path), "r") as zip_file_obj:
            zip_file_obj.extractall(extract_target_dir)
        logger.info(f"{zip_file_path} unzipped to {extract_target_dir}")

        target_md_file = extract_target_dir / "full.md"
        new_md_path = target_md_file.with_name(f"{pdf_stem}.md")
        target_md_file.rename(new_md_path)
        logger.info(f"{target_md_file} renamed to {pdf_stem}.md")
        return str(new_md_path.absolute())