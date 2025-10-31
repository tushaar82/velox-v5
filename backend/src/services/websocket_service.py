"""
WebSocket service for real-time updates.
Broadcasts trading events, position updates, and analytics to connected clients.
"""
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime

from ..utils.logging import get_logger


logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        # strategy_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # websocket -> user_id
        self.connection_users: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int, strategy_id: int | None = None):
        """
        Connect a WebSocket client.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            strategy_id: Optional strategy ID to subscribe to
        """
        await websocket.accept()
        self.connection_users[websocket] = user_id

        if strategy_id:
            if strategy_id not in self.active_connections:
                self.active_connections[strategy_id] = set()
            self.active_connections[strategy_id].add(websocket)

        logger.info(
            f"WebSocket connected: user_id={user_id}, strategy_id={strategy_id}",
            user_id=user_id,
            strategy_id=strategy_id
        )

    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client.

        Args:
            websocket: WebSocket connection
        """
        # Remove from all strategy subscriptions
        for strategy_id in list(self.active_connections.keys()):
            if websocket in self.active_connections[strategy_id]:
                self.active_connections[strategy_id].remove(websocket)

                # Clean up empty sets
                if not self.active_connections[strategy_id]:
                    del self.active_connections[strategy_id]

        # Remove from user mapping
        user_id = self.connection_users.pop(websocket, None)

        logger.info(
            f"WebSocket disconnected: user_id={user_id}",
            user_id=user_id
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send message to a specific connection.

        Args:
            message: Message to send
            websocket: Target WebSocket
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_strategy(self, strategy_id: int, message: dict):
        """
        Broadcast message to all clients subscribed to a strategy.

        Args:
            strategy_id: Strategy ID
            message: Message to broadcast
        """
        if strategy_id not in self.active_connections:
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        message_text = json.dumps(message)

        disconnected = []

        for connection in self.active_connections[strategy_id]:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_tick_update(self, strategy_id: int, tick_data: dict):
        """
        Broadcast tick update to strategy subscribers.

        Args:
            strategy_id: Strategy ID
            tick_data: Tick data
        """
        message = {
            "type": "tick_update",
            "strategy_id": strategy_id,
            "data": tick_data
        }
        await self.broadcast_to_strategy(strategy_id, message)

    async def broadcast_position_update(self, strategy_id: int, position_data: dict):
        """
        Broadcast position update to strategy subscribers.

        Args:
            strategy_id: Strategy ID
            position_data: Position data
        """
        message = {
            "type": "position_update",
            "strategy_id": strategy_id,
            "data": position_data
        }
        await self.broadcast_to_strategy(strategy_id, message)

    async def broadcast_order_update(self, strategy_id: int, order_data: dict):
        """
        Broadcast order update to strategy subscribers.

        Args:
            strategy_id: Strategy ID
            order_data: Order data
        """
        message = {
            "type": "order_update",
            "strategy_id": strategy_id,
            "data": order_data
        }
        await self.broadcast_to_strategy(strategy_id, message)

    async def broadcast_performance_update(self, strategy_id: int, metrics: dict):
        """
        Broadcast performance metrics update to strategy subscribers.

        Args:
            strategy_id: Strategy ID
            metrics: Performance metrics
        """
        message = {
            "type": "performance_update",
            "strategy_id": strategy_id,
            "data": metrics
        }
        await self.broadcast_to_strategy(strategy_id, message)

    async def broadcast_risk_alert(self, strategy_id: int, alert_data: dict):
        """
        Broadcast risk alert to strategy subscribers.

        Args:
            strategy_id: Strategy ID
            alert_data: Risk alert data
        """
        message = {
            "type": "risk_alert",
            "strategy_id": strategy_id,
            "data": alert_data,
            "severity": alert_data.get("severity", "info")
        }
        await self.broadcast_to_strategy(strategy_id, message)


# Global connection manager
ws_manager = ConnectionManager()
