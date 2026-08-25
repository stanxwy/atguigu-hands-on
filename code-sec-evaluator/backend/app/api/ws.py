"""WebSocket 接口：WS /api/projects/{project_id}/stream（握手鉴权，失败 close 4001）。"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api import deps
from app.core.constants import WS_UNAUTHORIZED_CODE
from app.core.errors import AppError
from app.ws.manager import manager

router = APIRouter()


@router.websocket("/api/projects/{project_id}/stream")
async def stream(websocket: WebSocket, project_id: int) -> None:
    """实时订阅：鉴权失败立即以 4001 关闭，服务端仅响应心跳 ping。"""
    token = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if not token:
        await websocket.close(code=WS_UNAUTHORIZED_CODE, reason="unauthorized")
        return

    try:
        user = await deps.authenticate_token(token)
        await deps.check_project_access(user, project_id)
    except AppError:
        await websocket.close(code=WS_UNAUTHORIZED_CODE, reason="unauthorized")
        return

    await websocket.accept()
    await manager.connect(project_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(project_id, websocket)
