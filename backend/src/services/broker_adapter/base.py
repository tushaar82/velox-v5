"""
Base broker adapter class defining the interface for all broker integrations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderRequest:
    """Order request data."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None

    # Strategy context
    strategy_instance_id: Optional[int] = None

    # Advanced order options
    validity: str = "DAY"  # DAY, IOC, GTD
    disclosed_quantity: Optional[int] = None

    # Additional metadata
    tag: Optional[str] = None


@dataclass
class OrderResponse:
    """Order response from broker."""
    broker_order_id: str
    order_id: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING
    message: Optional[str] = None

    # Execution details (filled when order is executed)
    filled_quantity: int = 0
    average_price: Optional[float] = None
    commission: float = 0.0
    tax: float = 0.0

    # Timestamps
    placed_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


@dataclass
class PositionInfo:
    """Position information from broker."""
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    pnl: float
    side: OrderSide

    # Additional details
    day_pnl: Optional[float] = None
    multiplier: int = 1

    # Metadata
    product_type: str = "MIS"  # MIS (intraday), CNC (delivery), NRML (normal)


@dataclass
class BalanceInfo:
    """Balance information from broker."""
    available_cash: float
    total_cash: float
    margin_used: float
    margin_available: float

    # Additional details
    collateral: Optional[float] = None
    unrealized_pnl: Optional[float] = None


class BrokerAdapter(ABC):
    """
    Abstract base class for broker adapters.

    All broker integrations must implement this interface to ensure
    consistency across different broker APIs.
    """

    def __init__(self, account_id: str, credentials: Dict[str, str]):
        """
        Initialize broker adapter.

        Args:
            account_id: Broker account identifier
            credentials: Dictionary containing API credentials
                (api_key, api_secret, access_token, etc.)
        """
        self.account_id = account_id
        self.credentials = credentials
        self._is_connected = False

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the broker name."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to broker API.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from broker API.

        Returns:
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """
        Place an order with the broker.

        Args:
            order_request: Order details

        Returns:
            OrderResponse with broker order ID and status

        Raises:
            BrokerException: If order placement fails
        """
        pass

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """
        Cancel an existing order.

        Args:
            broker_order_id: Broker's order identifier

        Returns:
            True if cancellation successful, False otherwise

        Raises:
            BrokerException: If cancellation fails
        """
        pass

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> OrderResponse:
        """
        Get the status of an order.

        Args:
            broker_order_id: Broker's order identifier

        Returns:
            OrderResponse with current status

        Raises:
            BrokerException: If status retrieval fails
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[PositionInfo]:
        """
        Get all open positions from broker.

        Returns:
            List of PositionInfo objects

        Raises:
            BrokerException: If positions retrieval fails
        """
        pass

    @abstractmethod
    async def get_balance(self) -> BalanceInfo:
        """
        Get account balance information.

        Returns:
            BalanceInfo with current balances

        Raises:
            BrokerException: If balance retrieval fails
        """
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current quote/price for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with quote data (price, bid, ask, volume, etc.)

        Raises:
            BrokerException: If quote retrieval fails
        """
        pass

    async def modify_order(
        self,
        broker_order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[OrderType] = None
    ) -> OrderResponse:
        """
        Modify an existing order.

        Default implementation cancels and replaces. Brokers that support
        native modification should override this method.

        Args:
            broker_order_id: Broker's order identifier
            quantity: New quantity (optional)
            price: New price (optional)
            order_type: New order type (optional)

        Returns:
            OrderResponse with new order details

        Raises:
            BrokerException: If modification fails
        """
        # Default implementation: cancel and replace
        # Specific brokers can override with native modify
        raise NotImplementedError(
            f"{self.broker_name} does not support order modification. "
            "Please cancel and place a new order."
        )

    def is_connected(self) -> bool:
        """Check if adapter is connected to broker."""
        return self._is_connected

    async def validate_credentials(self) -> bool:
        """
        Validate broker credentials.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            await self.connect()
            await self.disconnect()
            return True
        except Exception:
            return False


class BrokerException(Exception):
    """Exception raised for broker-related errors."""

    def __init__(self, message: str, broker_name: str, error_code: Optional[str] = None):
        self.broker_name = broker_name
        self.error_code = error_code
        super().__init__(f"[{broker_name}] {message}")
