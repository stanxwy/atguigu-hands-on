import json
import logging
import os

from minio import Minio
from minio.deleteobjects import DeleteObject

from app.domain.ports.object_store import ObjectStore
from app.infra.config.settings import Settings

logger = logging.getLogger(__name__)

_EXTENSION_TO_CONTENT_TYPE = {
    ".pdf": "application/pdf",
    ".doc": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}

class MinIOService(ObjectStore):

    def __init__(self, settings: Settings):
        self._settings = settings
        self._minio_client = None
        protocol = "https://" if settings.minio_secure else "http://"
        self._base_url = f"{protocol}{settings.minio_endpoint}/{settings.minio_bucket_name}"
        

    def _get_minio_client(self):
        minio_config = self._settings
        bucket_name = self._settings.minio_bucket_name
        if self._minio_client is None:
            try:
                logger.debug("Minio client initializing...")
                minio_client = Minio(
                    endpoint=minio_config.minio_endpoint,
                    access_key=minio_config.minio_access_key,
                    secret_key=minio_config.minio_secret_key,
                    secure=False)

                if not minio_client.bucket_exists(bucket_name):
                    minio_client.make_bucket(bucket_name)
                
                # allow public access
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                        }
                    ]
                }
                minio_client.set_bucket_policy(bucket_name, json.dumps(policy))
                logger.debug("MinIO client initialized")
                self._minio_client = minio_client
            except Exception as e:
                logger.exception(f"Minio init failed:{e!s}", stack_info=True)
        return self._minio_client

    def clean_dir(self, dir_path: str) -> None:
        try:
            minio_client = self._get_minio_client()
            objects_to_delete = minio_client.list_objects(
                self._settings.minio_bucket_name, 
                prefix=dir_path, 
                recursive=True)
            
            delete_list = [DeleteObject(obj.object_name) for obj in objects_to_delete]
            if delete_list:
                errors = minio_client.remove_objects(self._settings.minio_bucket_name, delete_list)
                for error in errors:
                    logger.error(f"Error deleting object: {error}")
        except Exception as e:
            logger.exception(f"Failed to clean directory {dir_path}: {e!s}", stack_info=True)

    def upload(self, local_path: str, object_name: str, content_type: str | None = None) -> str | None:
        try:
            # for multi-dot extensions, only the final suffix is split, e.g. test.tar.gz -> ("test.tar", ".gz")
            ext = os.path.splitext(local_path)[1][1:]
            self._get_minio_client().fput_object(
                bucket_name=self._settings.minio_bucket_name,
                object_name=object_name,
                file_path=local_path,
                content_type=content_type or _EXTENSION_TO_CONTENT_TYPE.get(ext)
            )
            return f"{self._base_url}/{object_name}"
        except Exception as e:
            logger.exception(f"Error uploading file {local_path}, message: {e!s}", stack_info=True)

    def clean_img_dir(self, doc_stem: str) -> None:
        img_dir = f"{self._settings.minio_img_dir}/{doc_stem}"
        self.clean_dir(img_dir)

    def upload_img(self, local_path: str, object_name: str, content_type: str = None) -> str | None:
        return self.upload(local_path, f"{self._settings.minio_img_dir}/{object_name}", content_type)