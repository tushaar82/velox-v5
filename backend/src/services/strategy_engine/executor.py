"""Strategy execution service."""
import asyncio
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import get_db
from src.models.market_data import Tick
from src.models.strategy import StrategyInstance, StrategyStatus
from src.models.trading import OrderSide, OrderStatus, OrderType, Position, PositionStatus, TradeOrder
from src.services.strategy_engine.base import BaseStrategy, Signal, StrategyContext, SimpleMovingAverageCrossover
from src.utils.logging import get_logger, log_strategy_execution, log_trade_order
from src.utils.monitoring import record_strategy_execution, record_trade_order

logger = get_logger(__name__)


class StrategyExecutor:
    """Execute trading strategies."""

    def __init__(self):
        self.active_strategies: Dict[UUID, BaseStrategy] = {}
        self.strategy_tasks: Dict[UUID, asyncio.Task] = {}

    async def start_strategy(self, strategy_id: UUID, db: AsyncSession) -> bool:
        """
        Start a trading strategy.

        Args:
            strategy_id: Strategy instance ID
            db: Database session

        Returns:
            True if started successfully
        """
        try:
            # Load strategy from database
            result = await db.execute(
                select(StrategyInstance).where(StrategyInstance.id == strategy_id)
            )
            strategy_instance = result.scalar_one_or_none()

            if not strategy_instance:
                logger.error("strategy_not_found", strategy_id=str(strategy_id))
                return False

            # Create strategy context
            context = StrategyContext(
                strategy_id=str(strategy_id),
                parameters=strategy_instance.parameters,
            )

            # Create strategy instance (using SMA crossover as example)
            strategy = SimpleMovingAverageCrossover(context)

            # Store active strategy
            self.active_strategies[strategy_id] = strategy

            # Update database status
            strategy_instance.status = StrategyStatus.ACTIVE
            strategy_instance.is_active = True
            await db.commit()

            log_strategy_execution(
                logger,
                str(strategy_id),
                ",".join(strategy_instance.symbols),
                "started",
                {"status": "success"},
            )
            record_strategy_execution(str(strategy_id), "started")

            return True

        except Exception as e:
            logger.error("strategy_start_failed", strategy_id=str(strategy_id), error=str(e))
            record_strategy_execution(str(strategy_id), "start_failed")
            return False

    async def stop_strategy(self, strategy_id: UUID, db: AsyncSession) -> bool:
        """
        Stop a trading strategy.

        Args:
            strategy_id: Strategy instance ID
            db: Database session

        Returns:
            True if stopped successfully
        """
        try:
            # Remove from active strategies
            if strategy_id in self.active_strategies:
                del self.active_strategies[strategy_id]

            # Update database
            result = await db.execute(
                select(StrategyInstance).where(StrategyInstance.id == strategy_id)
            )
            strategy_instance = result.scalar_one_or_none()

            if strategy_instance:
                strategy_instance.status = StrategyStatus.STOPPED
                strategy_instance.is_active = False
                await db.commit()

            log_strategy_execution(
                logger,
                str(strategy_id),
                "",
                "stopped",
                {"status": "success"},
            )
            record_strategy_execution(str(strategy_id), "stopped")

            return True

        except Exception as e:
            logger.error("strategy_stop_failed", strategy_id=str(strategy_id), error=str(e))
            return False

    async def process_tick(self, tick: Tick, db: AsyncSession) -> None:
        """
        Process tick for all active strategies.

        Args:
            tick: Market tick data
            db: Database session
        """
        for strategy_id, strategy in list(self.active_strategies.items()):
            try:
                # Check if strategy is interested in this symbol
                result = await db.execute(
                    select(StrategyInstance).where(StrategyInstance.id == strategy_id)
                )
                strategy_instance = result.scalar_one_or_none()

                if not strategy_instance or tick.symbol not in strategy_instance.symbols:
                    continue

                # Process tick
                signal = strategy.on_tick(tick)

                if signal:
                    await self._execute_signal(signal, strategy_id, db)

            except Exception as e:
                logger.error(
                    "tick_processing_error",
                    strategy_id=str(strategy_id),
                    symbol=tick.symbol,
                    error=str(e),
                )
                strategy.on_error(e)

    async def _execute_signal(
        self, signal: Signal, strategy_id: UUID, db: AsyncSession
    ) -> None:
        """
        Execute a trading signal.

        Args:
            signal: Trading signal
            strategy_id: Strategy instance ID
            db: Database session
        """
        try:
            # Create trade order
            order = TradeOrder(
                strategy_id=strategy_id,
                symbol=signal.symbol,
                order_type=signal.order_type,
                side=signal.side,
                quantity=signal.quantity,
                price=signal.price if signal.order_type == OrderType.LIMIT else None,
                status=OrderStatus.PENDING,
                metadata=signal.metadata,
            )

            db.add(order)
            await db.commit()
            await db.refresh(order)

            log_trade_order(
                logger,
                str(order.id),
                signal.symbol,
                signal.order_type.value,
                signal.side.value,
                signal.quantity,
                signal.price,
                OrderStatus.PENDING.value,
            )
            record_trade_order(signal.symbol, signal.side.value, OrderStatus.PENDING.value)

            # Simulate order execution (in production, send to broker)
            await self._simulate_order_execution(order, signal, strategy_id, db)

        except Exception as e:
            logger.error(
                "signal_execution_failed",
                strategy_id=str(strategy_id),
                symbol=signal.symbol,
                error=str(e),
            )

    async def _simulate_order_execution(
        self, order: TradeOrder, signal: Signal, strategy_id: UUID, db: AsyncSession
    ) -> None:
        """
        Simulate order execution (replace with real broker integration).

        Args:
            order: Trade order
            signal: Trading signal
            strategy_id: Strategy instance ID
            db: Database session
        """
        # Simulate filled order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_filled_price = signal.price

        # Create or update position
        if signal.side == OrderSide.BUY:
            # Open position
            position = Position(
                strategy_id=strategy_id,
                symbol=signal.symbol,
                side=signal.side,
                quantity=signal.quantity,
                entry_price=signal.price,
                current_price=signal.price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                status=PositionStatus.OPEN,
            )
            db.add(position)

            # Notify strategy
            if strategy_id in self.active_strategies:
                self.active_strategies[strategy_id].on_position_opened(position)

        elif signal.side == OrderSide.SELL:
            # Close position
            result = await db.execute(
                select(Position).where(
                    Position.strategy_id == strategy_id,
                    Position.symbol == signal.symbol,
                    Position.status == PositionStatus.OPEN,
                )
            )
            position = result.scalar_one_or_none()

            if position:
                position.status = PositionStatus.CLOSED
                position.current_price = signal.price
                pnl = (signal.price - position.entry_price) * position.quantity
                position.realized_pnl = pnl

                # Notify strategy
                if strategy_id in self.active_strategies:
                    self.active_strategies[strategy_id].on_position_closed(position, pnl)

        await db.commit()

        log_trade_order(
            logger,
            str(order.id),
            signal.symbol,
            signal.order_type.value,
            signal.side.value,
            signal.quantity,
            signal.price,
            OrderStatus.FILLED.value,
        )
        record_trade_order(signal.symbol, signal.side.value, OrderStatus.FILLED.value)


# Global strategy executor instance
strategy_executor = StrategyExecutor()
