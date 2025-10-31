"""
Zerodha Kite broker adapter.

This is a simulated adapter for demonstration purposes.
In production, this would integrate with Zerodha Kite API.
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


class ZerodhaAdapter(BrokerAdapter):
    """Zerodha Kite broker adapter implementation."""

    def __init__(self, account_id: str, credentials: Dict[str, str]):
        super().__init__(account_id, credentials)
        self._orders: Dict[str, OrderResponse] = {}
        self._positions: Dict[str, PositionInfo] = {}
        self._balance = BalanceInfo(
            available_cash=150000.0,
            total_cash=150000.0,
            margin_used=0.0,
            margin_available=150000.0,
        )

    @property
    def broker_name(self) -> str:
        return "Zerodha"

    async def connect(self) -> bool:
        """Establish connection to Zerodha Kite API."""
        try:
            logger.info(f"Connecting to Zerodha for account {self.account_id}")

            # Validate credentials
            if not self.credentials.get("api_key"):
                raise BrokerException("API key is required", self.broker_name)

            if not self.credentials.get("access_token"):
                raise BrokerException("Access token is required", self.broker_name)

            # Simulate connection delay
            await asyncio.sleep(0.1)

            self._is_connected = True
            logger.info(f"Successfully connected to Zerodha for account {self.account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Zerodha: {e}")
            self._is_connected = False
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def disconnect(self) -> bool:
        """Disconnect from Zerodha Kite API."""
        try:
            logger.info(f"Disconnecting from Zerodha for account {self.account_id}")
            self._is_connected = False
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Zerodha: {e}")
            return False

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order with Zerodha broker."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info(f"Placing order on Zerodha: {order_request.symbol} {order_request.side} {order_request.quantity}")

            # Generate broker order ID (Zerodha format)
            broker_order_id = f"ZD{datetime.utcnow().strftime('%y%m%d')}{uuid.uuid4().hex[:8].upper()}"

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

                # Zerodha has lower commission structure
                order_response.commission = min(order_request.quantity * 0.01, 20.0)  # Max ₹20 per order
                order_response.tax = order_request.quantity * order_response.average_price * 0.000325  # STT
                order_response.filled_at = datetime.utcnow()

                # Update positions
                await self._update_position(order_request, order_response)

            return order_response

        except Exception as e:
            logger.error(f"Failed to place order on Zerodha: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an existing order."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info(f"Cancelling order {broker_order_id} on Zerodha")

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
            order.message = "Order cancelled by user"

            return True

        except Exception as e:
            logger.error(f"Failed to cancel order on Zerodha: {e}")
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
            logger.error(f"Failed to get order status from Zerodha: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def get_positions(self) -> List[PositionInfo]:
        """Get all open positions from broker."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info("Fetching positions from Zerodha")
            await asyncio.sleep(0.05)
            return list(self._positions.values())

        except Exception as e:
            logger.error(f"Failed to get positions from Zerodha: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def get_balance(self) -> BalanceInfo:
        """Get account balance information."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info("Fetching balance from Zerodha")
            await asyncio.sleep(0.05)
            return self._balance

        except Exception as e:
            logger.error(f"Failed to get balance from Zerodha: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get current quote/price for a symbol."""
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info(f"Fetching quote for {symbol} from Zerodha")
            await asyncio.sleep(0.05)

            # Simulate quote data (Zerodha format)
            base_price = 100.0
            return {
                "instrument_token": 12345,
                "symbol": symbol,
                "last_price": base_price,
                "ohlc": {
                    "open": base_price - 1.0,
                    "high": base_price + 2.0,
                    "low": base_price - 2.0,
                    "close": base_price
                },
                "depth": {
                    "buy": [{"price": base_price - 0.05, "quantity": 100}],
                    "sell": [{"price": base_price + 0.05, "quantity": 100}]
                },
                "volume": 1500000,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get quote from Zerodha: {e}")
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(str(e), self.broker_name)

    async def modify_order(
        self,
        broker_order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None
    ) -> OrderResponse:
        """
        Modify an existing order.

        Zerodha supports native order modification.
        """
        if not self._is_connected:
            raise BrokerException("Not connected to broker", self.broker_name)

        try:
            logger.info(f"Modifying order {broker_order_id} on Zerodha")

            if broker_order_id not in self._orders:
                raise BrokerException(f"Order {broker_order_id} not found", self.broker_name)

            order = self._orders[broker_order_id]

            if order.status not in [OrderStatus.OPEN, OrderStatus.PENDING]:
                raise BrokerException(
                    f"Cannot modify order in {order.status} status",
                    self.broker_name
                )

            # Simulate modification
            await asyncio.sleep(0.05)

            # Update order with new parameters
            if quantity:
                order.filled_quantity = 0  # Reset filled quantity
            if price:
                order.average_price = price

            order.message = "Order modified successfully"

            return order

        except Exception as e:
            logger.error(f"Failed to modify order on Zerodha: {e}")
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
                    product_type="MIS"  # Zerodha intraday product
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
