"""Base strategy engine classes."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.market_data import Candle, Tick
from src.models.trading import OrderSide, OrderType, Position
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Signal:
    """Trading signal."""

    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        price: float,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.symbol = symbol
        self.side = side
        self.price = price
        self.quantity = quantity
        self.order_type = order_type
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class StrategyContext:
    """Context for strategy execution."""

    def __init__(self, strategy_id: str, parameters: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.parameters = parameters
        self.positions: Dict[str, Position] = {}
        self.pending_orders: List[Any] = []
        self.historical_data: Dict[str, List[Candle]] = {}
        self.current_tick: Optional[Tick] = None


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, context: StrategyContext):
        self.context = context
        self.logger = get_logger(f"strategy.{self.context.strategy_id}")

    @abstractmethod
    def on_tick(self, tick: Tick) -> Optional[Signal]:
        """
        Called when a new tick is received.

        Args:
            tick: The new tick data

        Returns:
            Optional trading signal
        """
        pass

    @abstractmethod
    def on_candle(self, candle: Candle) -> Optional[Signal]:
        """
        Called when a new candle is formed.

        Args:
            candle: The new candle data

        Returns:
            Optional trading signal
        """
        pass

    @abstractmethod
    def on_position_opened(self, position: Position) -> None:
        """
        Called when a position is opened.

        Args:
            position: The opened position
        """
        pass

    @abstractmethod
    def on_position_closed(self, position: Position, pnl: float) -> None:
        """
        Called when a position is closed.

        Args:
            position: The closed position
            pnl: Profit/loss from the position
        """
        pass

    @abstractmethod
    def on_error(self, error: Exception) -> None:
        """
        Called when an error occurs during strategy execution.

        Args:
            error: The error that occurred
        """
        pass

    def should_enter_trade(self, symbol: str) -> bool:
        """
        Check if strategy should enter a new trade.

        Args:
            symbol: The symbol to check

        Returns:
            True if should enter trade
        """
        # Check if max positions reached
        max_positions = self.context.parameters.get("max_positions", 5)
        if len(self.context.positions) >= max_positions:
            return False

        # Check if already in position for this symbol
        if symbol in self.context.positions:
            return False

        return True

    def should_exit_trade(self, symbol: str, current_price: float) -> bool:
        """
        Check if strategy should exit an existing trade.

        Args:
            symbol: The symbol to check
            current_price: Current market price

        Returns:
            True if should exit trade
        """
        if symbol not in self.context.positions:
            return False

        position = self.context.positions[symbol]

        # Check stop loss
        if position.stop_loss:
            if position.side == OrderSide.BUY and current_price <= position.stop_loss:
                return True
            if position.side == OrderSide.SELL and current_price >= position.stop_loss:
                return True

        # Check take profit
        if position.take_profit:
            if position.side == OrderSide.BUY and current_price >= position.take_profit:
                return True
            if position.side == OrderSide.SELL and current_price <= position.take_profit:
                return True

        return False

    def calculate_position_size(self, symbol: str, price: float) -> float:
        """
        Calculate position size based on strategy parameters.

        Args:
            symbol: The symbol
            price: Entry price

        Returns:
            Position size (quantity)
        """
        position_size = self.context.parameters.get("position_size", 1.0)
        return position_size

    def calculate_stop_loss(
        self, symbol: str, side: OrderSide, entry_price: float
    ) -> Optional[float]:
        """
        Calculate stop loss price.

        Args:
            symbol: The symbol
            side: Order side
            entry_price: Entry price

        Returns:
            Stop loss price
        """
        stop_loss_percent = self.context.parameters.get("stop_loss_percent")
        if not stop_loss_percent:
            return None

        if side == OrderSide.BUY:
            return entry_price * (1 - stop_loss_percent / 100)
        else:
            return entry_price * (1 + stop_loss_percent / 100)

    def calculate_take_profit(
        self, symbol: str, side: OrderSide, entry_price: float
    ) -> Optional[float]:
        """
        Calculate take profit price.

        Args:
            symbol: The symbol
            side: Order side
            entry_price: Entry price

        Returns:
            Take profit price
        """
        take_profit_percent = self.context.parameters.get("take_profit_percent")
        if not take_profit_percent:
            return None

        if side == OrderSide.BUY:
            return entry_price * (1 + take_profit_percent / 100)
        else:
            return entry_price * (1 - take_profit_percent / 100)


class SimpleMovingAverageCrossover(BaseStrategy):
    """Example: Simple Moving Average Crossover Strategy."""

    def __init__(self, context: StrategyContext):
        super().__init__(context)
        self.fast_period = context.parameters.get("fast_period", 10)
        self.slow_period = context.parameters.get("slow_period", 20)
        self.prices: Dict[str, List[float]] = {}

    def on_tick(self, tick: Tick) -> Optional[Signal]:
        """Process tick data."""
        symbol = tick.symbol

        # Store price
        if symbol not in self.prices:
            self.prices[symbol] = []
        self.prices[symbol].append(tick.last_price)

        # Keep only necessary data
        max_period = max(self.fast_period, self.slow_period)
        if len(self.prices[symbol]) > max_period + 10:
            self.prices[symbol] = self.prices[symbol][-max_period - 10 :]

        # Need enough data
        if len(self.prices[symbol]) < self.slow_period:
            return None

        # Calculate moving averages
        fast_ma = sum(self.prices[symbol][-self.fast_period :]) / self.fast_period
        slow_ma = sum(self.prices[symbol][-self.slow_period :]) / self.slow_period

        # Generate signals
        if fast_ma > slow_ma and self.should_enter_trade(symbol):
            return Signal(
                symbol=symbol,
                side=OrderSide.BUY,
                price=tick.last_price,
                quantity=self.calculate_position_size(symbol, tick.last_price),
                stop_loss=self.calculate_stop_loss(symbol, OrderSide.BUY, tick.last_price),
                take_profit=self.calculate_take_profit(symbol, OrderSide.BUY, tick.last_price),
            )
        elif fast_ma < slow_ma and symbol in self.context.positions:
            return Signal(
                symbol=symbol,
                side=OrderSide.SELL,
                price=tick.last_price,
                quantity=self.context.positions[symbol].quantity,
            )

        return None

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        """Process candle data."""
        return None

    def on_position_opened(self, position: Position) -> None:
        """Handle position opened."""
        self.logger.info("position_opened", symbol=position.symbol, side=position.side.value)

    def on_position_closed(self, position: Position, pnl: float) -> None:
        """Handle position closed."""
        self.logger.info("position_closed", symbol=position.symbol, pnl=pnl)

    def on_error(self, error: Exception) -> None:
        """Handle error."""
        self.logger.error("strategy_error", error=str(error))
