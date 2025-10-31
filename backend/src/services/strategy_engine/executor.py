"""
Strategy execution service.
Manages strategy instances and executes trades based on signals.
"""
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ...models.strategy import StrategyInstance, StrategyStatus, TradingMode
from ...models.trading import (
    TradeOrder, Position, OrderType, OrderSide, OrderStatus, PositionStatus, TradeExecution
)
from ...models.market_data import Tick
from ...models.user import BrokerAccount
from ...utils.logging import get_logger, log_strategy_execution, log_performance, log_risk_event
from ...utils.monitoring import trade_execution_histogram, PerformanceTracker
from .base import StrategyEngine, Signal
from .risk_manager import risk_manager
from .trailing_stoploss import trailing_stoploss_service
from ..trading_mode_service import trading_mode_service
from ..broker_adapter.factory import BrokerAdapterFactory
from ..broker_adapter.base import (
    BrokerAdapter,
    BrokerException,
    OrderRequest,
    OrderType as BrokerOrderType,
    OrderSide as BrokerOrderSide,
)


logger = get_logger(__name__)


class StrategyExecutor:
    """Executes trading strategies and manages orders."""

    def __init__(self):
        """Initialize strategy executor."""
        self.active_strategies: Dict[int, StrategyEngine] = {}
        self.risk_manager = risk_manager

    async def start_strategy(
        self,
        strategy_instance: StrategyInstance,
        strategy_engine: StrategyEngine,
        db: AsyncSession
    ) -> bool:
        """
        Start a strategy instance.

        Args:
            strategy_instance: Strategy instance to start
            strategy_engine: Strategy engine implementation
            db: Database session

        Returns:
            True if started successfully
        """
        try:
            # Update strategy status
            strategy_instance.status = StrategyStatus.ACTIVE
            strategy_instance.started_at = datetime.utcnow()

            await db.commit()

            # Add to active strategies
            self.active_strategies[strategy_instance.id] = strategy_engine

            log_strategy_execution(
                strategy_id=str(strategy_instance.id),
                action="started",
                details={"symbols": strategy_instance.symbols}
            )

            logger.info(f"Strategy {strategy_instance.id} started")
            return True

        except Exception as e:
            logger.error(f"Error starting strategy: {e}", exc_info=True)
            await db.rollback()
            return False

    async def stop_strategy(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Stop a strategy instance.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            True if stopped successfully
        """
        try:
            # Update strategy status
            await db.execute(
                update(StrategyInstance)
                .where(StrategyInstance.id == strategy_instance_id)
                .values(
                    status=StrategyStatus.STOPPED,
                    stopped_at=datetime.utcnow()
                )
            )
            await db.commit()

            # Remove from active strategies
            if strategy_instance_id in self.active_strategies:
                del self.active_strategies[strategy_instance_id]

            log_strategy_execution(
                strategy_id=str(strategy_instance_id),
                action="stopped"
            )

            logger.info(f"Strategy {strategy_instance_id} stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping strategy: {e}", exc_info=True)
            await db.rollback()
            return False

    async def send_order_to_broker(
        self,
        order: TradeOrder,
        strategy_instance: StrategyInstance,
        db: AsyncSession
    ) -> Optional[TradeExecution]:
        """
        Send order to broker for execution.

        Args:
            order: Trade order to execute
            strategy_instance: Strategy instance
            db: Database session

        Returns:
            TradeExecution record if successful, None otherwise
        """
        try:
            # Skip broker execution for paper trading mode
            if strategy_instance.trading_mode == TradingMode.PAPER:
                logger.info(f"Order {order.id} is in paper trading mode, skipping broker execution")
                # Simulate immediate fill for paper trading
                order.status = OrderStatus.FILLED
                order.filled_quantity = order.quantity
                order.average_fill_price = order.price or 100.0  # Use order price or default
                order.filled_at = datetime.utcnow()
                await db.commit()
                return None

            # Get broker adapter for the user
            try:
                broker_adapter = await BrokerAdapterFactory.create_adapter_for_user(
                    user_id=order.user_id,
                    db=db
                )
            except BrokerException as e:
                logger.error(f"Failed to create broker adapter: {e}")
                order.status = OrderStatus.REJECTED
                order.rejection_reason = str(e)
                await db.commit()
                return None

            # Connect to broker
            if not broker_adapter.is_connected():
                await broker_adapter.connect()

            # Map order types
            broker_order_type = BrokerOrderType.MARKET
            if order.order_type == OrderType.LIMIT:
                broker_order_type = BrokerOrderType.LIMIT
            elif order.order_type == OrderType.STOP:
                broker_order_type = BrokerOrderType.STOP

            # Map order side
            broker_order_side = BrokerOrderSide.BUY if order.side == OrderSide.BUY else BrokerOrderSide.SELL

            # Create broker order request
            broker_order_request = OrderRequest(
                symbol=order.symbol,
                side=broker_order_side,
                order_type=broker_order_type,
                quantity=order.quantity,
                price=order.price,
                stop_price=order.stop_price,
                strategy_instance_id=strategy_instance.id
            )

            # Place order with broker
            try:
                broker_response = await broker_adapter.place_order(broker_order_request)
                logger.info(f"Order placed with broker: {broker_response.broker_order_id}")

                # Update order with broker details
                order.broker_order_id = broker_response.broker_order_id
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = broker_response.placed_at or datetime.utcnow()

                # If order is already filled (market orders may fill immediately)
                if broker_response.status.value == OrderStatus.FILLED.value:
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = broker_response.filled_quantity
                    order.average_fill_price = broker_response.average_price
                    order.commission = broker_response.commission
                    order.filled_at = broker_response.filled_at

                    # Create trade execution record
                    # Get broker account ID from the adapter context (would need to be stored)
                    # For now, we'll need to query it
                    broker_account_result = await db.execute(
                        select(BrokerAccount).where(
                            BrokerAccount.user_id == order.user_id,
                            BrokerAccount.is_primary == True,
                            BrokerAccount.is_active == True
                        )
                    )
                    broker_account = broker_account_result.scalar_one_or_none()

                    if broker_account:
                        trade_execution = TradeExecution(
                            order_id=order.id,
                            broker_account_id=broker_account.id,
                            symbol=order.symbol,
                            side=order.side,
                            quantity=broker_response.filled_quantity,
                            price=broker_response.average_price,
                            broker_execution_id=broker_response.broker_order_id,
                            broker_order_id=broker_response.broker_order_id,
                            commission=broker_response.commission,
                            tax=broker_response.tax,
                            total_cost=(broker_response.filled_quantity * broker_response.average_price +
                                       broker_response.commission + broker_response.tax),
                            executed_at=broker_response.filled_at or datetime.utcnow()
                        )
                        db.add(trade_execution)

                await db.commit()

                # Disconnect from broker
                await broker_adapter.disconnect()

                return trade_execution if 'trade_execution' in locals() else None

            except BrokerException as e:
                logger.error(f"Broker rejected order: {e}")
                order.status = OrderStatus.REJECTED
                order.rejection_reason = str(e)
                await db.commit()

                # Disconnect from broker
                await broker_adapter.disconnect()
                return None

        except Exception as e:
            logger.error(f"Error sending order to broker: {e}", exc_info=True)
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            await db.commit()
            return None

    @log_performance("trade_execution_latency")
    async def execute_signal(
        self,
        signal: Signal,
        strategy_instance_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Optional[TradeOrder]:
        """
        Execute a trading signal.

        Args:
            signal: Trading signal
            strategy_instance_id: Strategy instance ID
            user_id: User ID
            db: Database session

        Returns:
            Created trade order if successful
        """
        with PerformanceTracker(trade_execution_histogram):
            try:
                # Check risk limits before executing
                is_within_limits, violation = await self.risk_manager.check_risk_limits(
                    strategy_instance_id,
                    user_id,
                    db
                )

                if not is_within_limits and violation:
                    log_risk_event(
                        event_type="trade_blocked_risk_limit",
                        severity="warning",
                        details={
                            "strategy_id": strategy_instance_id,
                            "violation": violation.violation_type,
                            "message": violation.message
                        }
                    )

                    # Close all positions if critical violation
                    if violation.severity == "critical":
                        await self.risk_manager.close_all_positions(
                            strategy_instance_id,
                            f"Risk limit breached: {violation.message}",
                            db
                        )

                        # Stop strategy
                        await self.stop_strategy(strategy_instance_id, db)

                    logger.warning(
                        f"Trade blocked due to risk limit: {violation.message}",
                        strategy_id=strategy_instance_id
                    )
                    return None

                # Check position size limit for entry signals
                if signal.signal_type == 'entry':
                    quantity = self._calculate_quantity(signal)
                    position_value = signal.price * quantity

                    is_allowed, reason = await self.risk_manager.check_position_size_limit(
                        strategy_instance_id,
                        user_id,
                        position_value,
                        db
                    )

                    if not is_allowed:
                        logger.warning(
                            f"Trade blocked: {reason}",
                            strategy_id=strategy_instance_id
                        )
                        return None
                # Create trade order
                order = TradeOrder(
                    strategy_instance_id=strategy_instance_id,
                    user_id=user_id,
                    symbol=signal.symbol,
                    order_type=OrderType.MARKET,  # Default to market order
                    side=signal.side,
                    quantity=self._calculate_quantity(signal),
                    price=signal.price if signal.signal_type == 'limit' else None,
                    status=OrderStatus.PENDING
                )

                db.add(order)
                await db.commit()
                await db.refresh(order)

                log_strategy_execution(
                    strategy_id=str(strategy_instance_id),
                    action="order_created",
                    details={
                        "order_id": order.id,
                        "symbol": signal.symbol,
                        "side": signal.side.value,
                        "quantity": order.quantity
                    }
                )

                # Get strategy instance for broker execution
                result = await db.execute(
                    select(StrategyInstance)
                    .where(StrategyInstance.id == strategy_instance_id)
                )
                strategy_instance = result.scalar_one_or_none()

                if not strategy_instance:
                    logger.error(f"Strategy instance {strategy_instance_id} not found")
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = "Strategy instance not found"
                    await db.commit()
                    return None

                # Send order to broker for execution
                trade_execution = await self.send_order_to_broker(order, strategy_instance, db)

                # If order was filled immediately, open position
                if order.status == OrderStatus.FILLED and order.filled_quantity > 0:
                    await self.open_position(order, order.average_fill_price, db)

                logger.info(
                    f"Order {order.id} submitted for strategy {strategy_instance_id}",
                    order_id=order.id,
                    symbol=signal.symbol,
                    status=order.status.value
                )

                return order

            except Exception as e:
                logger.error(f"Error executing signal: {e}", exc_info=True)
                await db.rollback()
                return None

    async def open_position(
        self,
        order: TradeOrder,
        filled_price: float,
        db: AsyncSession
    ) -> Optional[Position]:
        """
        Open a new position from filled order.

        Args:
            order: Filled trade order
            filled_price: Actual fill price
            db: Database session

        Returns:
            Created position
        """
        try:
            position = Position(
                strategy_instance_id=order.strategy_instance_id,
                user_id=order.user_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.filled_quantity,
                entry_price=filled_price,
                entry_time=datetime.utcnow(),
                current_price=filled_price,
                status=PositionStatus.OPEN
            )

            db.add(position)
            await db.commit()
            await db.refresh(position)

            # Get strategy instance to check trading mode
            result = await db.execute(
                select(StrategyInstance)
                .where(StrategyInstance.id == order.strategy_instance_id)
            )
            instance = result.scalar_one_or_none()

            # Execute in paper trading mode if applicable
            if instance and instance.trading_mode == TradingMode.PAPER:
                await trading_mode_service.execute_paper_trade(
                    order,
                    filled_price,
                    order.user_id,
                    db
                )

            log_strategy_execution(
                strategy_id=str(order.strategy_instance_id),
                action="position_opened",
                details={
                    "position_id": position.id,
                    "symbol": order.symbol,
                    "entry_price": filled_price,
                    "trading_mode": instance.trading_mode.value if instance else "unknown"
                }
            )

            # Check if strategy has trailing stoploss enabled
            if instance and instance.trailing_stoploss_enabled and instance.trailing_stoploss_percentage:
                # Create trailing stoploss for this position
                await trailing_stoploss_service.create_trailing_stoploss(
                    position,
                    instance.trailing_stoploss_percentage,
                    None,  # Can add trailing_amount support later
                    db
                )

            logger.info(
                f"Position {position.id} opened in {instance.trading_mode.value if instance else 'unknown'} mode",
                position_id=position.id,
                symbol=order.symbol
            )

            return position

        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)
            await db.rollback()
            return None

    async def close_position(
        self,
        position: Position,
        exit_price: float,
        db: AsyncSession
    ) -> bool:
        """
        Close an existing position.

        Args:
            position: Position to close
            exit_price: Exit price
            db: Database session

        Returns:
            True if closed successfully
        """
        try:
            # Update position
            position.exit_price = exit_price
            position.exit_time = datetime.utcnow()
            position.status = PositionStatus.CLOSED

            # Calculate realized P&L
            if position.side == OrderSide.BUY:
                pnl = (exit_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - exit_price) * position.quantity

            position.realized_pnl = pnl

            # Get strategy instance to check trading mode
            result = await db.execute(
                select(StrategyInstance)
                .where(StrategyInstance.id == position.strategy_instance_id)
            )
            instance = result.scalar_one_or_none()

            # Handle paper trading mode
            if instance and instance.trading_mode == TradingMode.PAPER:
                await trading_mode_service.close_paper_position(
                    position,
                    exit_price,
                    position.user_id,
                    db
                )

            await db.commit()

            log_strategy_execution(
                strategy_id=str(position.strategy_instance_id),
                action="position_closed",
                details={
                    "position_id": position.id,
                    "symbol": position.symbol,
                    "pnl": pnl,
                    "trading_mode": instance.trading_mode.value if instance else "unknown"
                }
            )

            logger.info(
                f"Position {position.id} closed with P&L: {pnl} in {instance.trading_mode.value if instance else 'unknown'} mode",
                position_id=position.id,
                pnl=pnl
            )

            return True

        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            await db.rollback()
            return False

    async def update_position_price(
        self,
        position: Position,
        current_price: float,
        db: AsyncSession
    ) -> Optional[bool]:
        """
        Update position with current market price and check trailing stoploss.

        Args:
            position: Position to update
            current_price: Current market price
            db: Database session

        Returns:
            True if trailing stoploss was triggered, None otherwise
        """
        try:
            position.current_price = current_price

            # Calculate unrealized P&L
            if position.side == OrderSide.BUY:
                pnl = (current_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - current_price) * position.quantity

            position.unrealized_pnl = pnl

            # Check and update trailing stoploss
            stoploss_triggered = await trailing_stoploss_service.update_trailing_stoploss(
                position,
                current_price,
                db
            )

            # If stoploss triggered, close the position
            if stoploss_triggered:
                await self.close_position(position, current_price, db)
                logger.info(
                    f"Position {position.id} closed by trailing stoploss",
                    position_id=position.id,
                    symbol=position.symbol
                )
                return True

            await db.commit()
            return None

        except Exception as e:
            logger.error(f"Error updating position: {e}", exc_info=True)
            await db.rollback()
            return None

    def _calculate_quantity(self, signal: Signal) -> int:
        """
        Calculate order quantity from signal.

        Args:
            signal: Trading signal

        Returns:
            Order quantity
        """
        # Default quantity calculation
        # Should be based on risk parameters and signal strength
        base_quantity = 100
        quantity = int(base_quantity * signal.strength)
        return max(1, quantity)

    async def get_active_positions(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> List[Position]:
        """
        Get all active positions for a strategy.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            List of open positions
        """
        result = await db.execute(
            select(Position)
            .where(
                Position.strategy_instance_id == strategy_instance_id,
                Position.status == PositionStatus.OPEN
            )
        )
        return list(result.scalars().all())


# Global strategy executor instance
strategy_executor = StrategyExecutor()
