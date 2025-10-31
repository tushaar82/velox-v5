"""
NSE (National Stock Exchange) broker adapter.

This is a simulated adapter for demonstration purposes.
In production, this would integrate with actual NSE broker APIs.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .base import (
    BrokerAdapter,
    BrokerException,
    OrderRequest,
    OrderResponse,
    PositionInfo,
    BalanceInfo,
    OrderStatus,
    OrderSide,
)

logger = logging.getLogger(__name__)


class NSEAdapter(BrokerAdapter):
    """NSE broker adapter implementation."""

    def __init__(self, account_id: str, credentials: Dict[str, str]):
        super().__init__(account_id, credentials)
        self._orders: Dict[str, OrderResponse] = {}
        self._positions: Dict[str, PositionInfo] = {}
        self._balance = BalanceInfo(
            available_cash=100000.0,
            total_cash=100000.0,
            margin_used=0.0,
            margin_available=100000.0,
        )

    @property
    def broker_name(self) -> str:
        return "NSE"

    async def connect(self) -> bool:
        """Establish connection to NSE broker API."""
        try:
            logger.info(f"Connecting to NSE for account {self.account_id}")

            # Validate credentials
            if not self.credentials.get("api_key"):
                raise BrokerException("API key is required", self.broker_name)

            if not self.credentials.get("api_secret"):
                raise BrokerException("API secret is required", self.broker_name)

            # Simulate connection delay
            await asyncio.sleep(0.1)

            self._is_connected = True
            logger.info(f"Successfully connected to NSE for account {self.account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to NSE: {e}")
            self._is_connected = False
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def disconnect(self) -> bool:
        """Disconnect from NSE broker API."""
        try:
            logger.info(f"Disconnecting from NSE for account {self.account_id}")
            self._is_connected = False
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from NSE: {e}")
            return False

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order with NSE broker."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info(f"Placing order on NSE: {order_request.symbol} {order_request.side} {order_request.quantity}")

            # Generate broker order ID
            broker_order_id = f"NSE{uuid.uuid4().hex[:12].upper()}"

            # Simulate order placement
            await asyncio.sleep(0.05)

            # Create order response
            order_response = OrderResponse(
                broker_order_id=broker_order_id,
                status=OrderStatus.OPEN,
                message="Order placed successfully",
                placed_at=datetime.utcnow(),
            )

            # Store order
            self._orders[broker_order_id] = order_response

            # Simulate immediate fill for market orders
            if order_request.order_type.value == "market":
                await asyncio.sleep(0.1)
                order_response.status = OrderStatus.FILLED
                order_response.filled_quantity = order_request.quantity
                order_response.average_price = order_request.price or 100.0
                order_response.commission = order_request.quantity * 0.03  # 0.03% commission
                order_response.tax = order_request.quantity * order_response.average_price * 0.000325  # STT
                order_response.filled_at = datetime.utcnow()

                # Update positions
                await self._update_position(order_request, order_response)

            return order_response

        except Exception as e:
            logger.error(f"Failed to place order on NSE: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an existing order."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info(f"Cancelling order {broker_order_id} on NSE")

            if broker_order_id not in self._orders:
                raise BrokerException(f"Order {broker_order_id} not found", self.broker_name)

            order = self._orders[broker_order_id]

            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                raise BrokerException(
                    f"Cannot cancel order in {order.status} status",
                    self.broker_name
                )

            # Simulate cancellation
            await asyncio.sleep(0.05)
            order.status = OrderStatus.CANCELLED
            order.message = "Order cancelled"

            return True

        except Exception as e:
            logger.error(f"Failed to cancel order on NSE: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def get_order_status(self, broker_order_id: str) -> OrderResponse:
        """Get the status of an order."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            if broker_order_id not in self._orders:
                raise BrokerException(f"Order {broker_order_id} not found", self.broker_name)

            return self._orders[broker_order_id]

        except Exception as e:
            logger.error(f"Failed to get order status from NSE: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def get_positions(self) -> List[PositionInfo]:
        """Get all open positions from broker."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info("Fetching positions from NSE")
            await asyncio.sleep(0.05)
            return list(self._positions.values())

        except Exception as e:
            logger.error(f"Failed to get positions from NSE: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def get_balance(self) -> BalanceInfo:
        """Get account balance information."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info("Fetching balance from NSE")
            await asyncio.sleep(0.05)
            return self._balance

        except Exception as e:
            logger.error(f"Failed to get balance from NSE: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get current quote/price for a symbol."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info(f"Fetching quote for {symbol} from NSE")
            await asyncio.sleep(0.05)

            # Simulate quote data
            base_price = 100.0
            return {
                "symbol": symbol,
                "last_price": base_price,
                "bid": base_price - 0.05,
                "ask": base_price + 0.05,
                "volume": 1000000,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get quote from NSE: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def _update_position(self, order_request: OrderRequest, order_response: OrderResponse):
        """Update internal position tracking."""
        symbol = order_request.symbol

        if symbol in self._positions:
            position = self._positions[symbol]

            if order_request.side == OrderSide.BUY:
                new_quantity = position.quantity + order_response.filled_quantity
                total_cost = (position.average_price * position.quantity +
                             order_response.average_price * order_response.filled_quantity)
                position.average_price = total_cost / new_quantity if new_quantity > 0 else 0
                position.quantity = new_quantity
            else:  # SELL
                position.quantity -= order_response.filled_quantity

            # Remove position if quantity is 0
            if position.quantity == 0:
                del self._positions[symbol]
        else:
            # New position
            if order_request.side == OrderSide.BUY:
                self._positions[symbol] = PositionInfo(
                    symbol=symbol,
                    quantity=order_response.filled_quantity,
                    average_price=order_response.average_price,
                    current_price=order_response.average_price,
                    pnl=0.0,
                    side=OrderSide.BUY,
                )

        # Update balance
        cost = order_response.filled_quantity * order_response.average_price
        total_cost = cost + order_response.commission + order_response.tax

        if order_request.side == OrderSide.BUY:
            self._balance.available_cash -= total_cost
            self._balance.margin_used += cost
        else:
            self._balance.available_cash += (cost - order_response.commission - order_response.tax)
            self._balance.margin_used -= cost if self._balance.margin_used >= cost else self._balance.margin_used
