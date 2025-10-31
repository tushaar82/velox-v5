"""
WebSocket API endpoints.
Provides real-time updates for trading data.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.database import get_db
from ...services.websocket_service import ws_manager
from ...core.security import decode_token
from ...utils.logging import get_logger


router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/strategy/{strategy_id}")
async def websocket_strategy_feed(
    websocket: WebSocket,
    strategy_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time strategy updates.

    Clients must provide a valid JWT token in the query parameter.
    Broadcasts: tick updates, position updates, order updates, performance metrics, risk alerts
    """
    try:
        # Verify token
        payload = decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Connect client
        await ws_manager.connect(websocket, user_id, strategy_id)

        # Send welcome message
        await ws_manager.send_personal_message(
            f'{{"type": "connected", "message": "Connected to strategy {strategy_id} feed"}}',
            websocket
        )

        # Keep connection alive and handle messages
        try:
            while True:
                # Receive any messages from client (like ping/pong)
                data = await websocket.receive_text()

                # Echo back for heartbeat
                if data == "ping":
                    await ws_manager.send_personal_message('{"type": "pong"}', websocket)

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for strategy {strategy_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        ws_manager.disconnect(websocket)


@router.websocket("/live")
async def websocket_live_feed(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for general live trading feed.

    Broadcasts general market updates and system notifications.
    """
    try:
        # Verify token
        payload = decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Connect client (no specific strategy)
        await ws_manager.connect(websocket, user_id, None)

        # Send welcome message
        await ws_manager.send_personal_message(
            '{"type": "connected", "message": "Connected to live feed"}',
            websocket
        )

        # Keep connection alive
        try:
            while True:
                data = await websocket.receive_text()

                if data == "ping":
                    await ws_manager.send_personal_message('{"type": "pong"}', websocket)

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected from live feed")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        ws_manager.disconnect(websocket)
