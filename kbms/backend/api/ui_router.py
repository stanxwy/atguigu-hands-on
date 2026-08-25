import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ui"])

STATIC_ROOT = Path(__file__).parent.parent / "static"


def _html(path: Path):
    if not path.exists():
        logger.error(f"Page not found: {path}")
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(path)


@router.get("/ingest", include_in_schema=False)
async def ingest_page():
    return _html(STATIC_ROOT / "pages" / "ingest.html")


@router.get("/chat", include_in_schema=False)
async def chat_page():
    return _html(STATIC_ROOT / "pages" / "chat.html")