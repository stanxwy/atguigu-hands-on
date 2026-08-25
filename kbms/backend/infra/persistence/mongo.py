import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import DESCENDING, MongoClient

from app.domain.ports.doc_store import DocumentStore
from app.infra.config.settings import Settings

logger = logging.getLogger(__name__)

class MongoDBClient:
    def __init__(self, settings: Settings):
        try:
            self.mongo_url = settings.mongo_url
            self.db_name = settings.mongo_db_name
            self.client = MongoClient(self.mongo_url)
            self.db = self.client[self.db_name]
            self.chat_message = self.db["chat_message"]

            self.chat_message.create_index([("session_id", 1), ("ts", -1)])
            logger.info(f"Successfully connected to MongoDB: {self.db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise


class MongoService(DocumentStore):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._mongo_client = None

    def _get_mongo_client(self):
        if self._mongo_client is None:
            self._mongo_client = MongoDBClient(self._settings)
        return self._mongo_client

    def clear_history(self, session_id: str) -> int:
        try:
            result = self._get_mongo_client().chat_message.delete_many({"session_id": session_id})
            logger.info(f"Deleted {result.deleted_count} messages for session {session_id}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error clearing history for session {session_id}: {e}")
            return 0

    def save_chat_message(
        self,
        session_id: str,
        role: str,
        text: str,
        rewritten_query: str = "",
        item_names: list[str] | None = None,
        image_urls: list[str] | None = None,
        message_id: str | None = None
    ) -> str:
        document = {
            "session_id": session_id,
            "role": role,
            "text": text,
            "rewritten_query": rewritten_query or "",
            "item_names": item_names,
            "image_urls": image_urls,
        }

        mongo_client = self._get_mongo_client()
        if message_id:
            result = mongo_client.chat_message.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": document}              
            )
            logger.info(f"Chat message updated: {document}")
            return message_id
        else:
            document["ts"] = datetime.now().timestamp()
            result = mongo_client.chat_message.insert_one(document)
            logger.info(f"Chat message inserted: {document}")
            return str(result.inserted_id)

    def update_message_item_names(self, ids: list[str], item_names: list[str]) -> int:
        try:
            result = self._get_mongo_client().chat_message.update_many(
                {
                    "_id": {"$in": [ObjectId(i) for i in ids]}
                },
                {"$set": {"item_names": item_names}}
            )
            logger.info(f"Updated {result.modified_count} records with item_names: {item_names}")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating history item_names: {e}")
            return 0

    def get_recent_messages(self, session_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        try:
            query = {"session_id": session_id} if session_id else {}
            cursor = self._get_mongo_client().chat_message.find(query).sort("ts", DESCENDING).limit(limit)
            messages = list(cursor)[::-1]
            for m in messages:
                logger.debug(f'{datetime.fromtimestamp(m["ts"]).strftime("%Y-%m-%d %H:%M:%S")} - {m["role"]}: {m["text"]}')
            return messages
        except Exception as e:
            logger.exception(f"Error getting recent messages: {e!s}", stack_info=True)
            return []