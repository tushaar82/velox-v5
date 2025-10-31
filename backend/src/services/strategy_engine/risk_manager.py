"""
Risk management service.
Monitors risk parameters, daily loss limits, and drawdowns.
Automatically closes positions when risk limits are breached.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ...models.user import RiskParameters
from ...models.strategy import StrategyInstance
from ...models.trading import Position, TradeOrder, PositionStatus, OrderSide
from ...utils.logging import get_logger, log_risk_event, log_performance
from ...utils.monitoring import risk_management_histogram, PerformanceTracker, risk_limit_breaches_counter


logger = get_logger(__name__)


class RiskViolation:
    """Represents a risk limit violation."""

    def __init__(
        self,
        violation_type: str,
        current_value: float,
        limit_value: float,
        severity: str,
        message: str
    ):
        self.violation_type = violation_type
        self.current_value = current_value
        self.limit_value = limit_value
        self.severity = severity  # 'warning', 'critical'
        self.message = message
        self.timestamp = datetime.utcnow()


class RiskManager:
    """
    Manages risk parameters and enforces risk limits.
    Monitors daily loss, drawdown, and position sizing.
    """

    def __init__(self):
        """Initialize risk manager."""
        self.daily_pnl_cache: Dict[int, float] = {}  # strategy_id -> daily_pnl
        self.peak_equity_cache: Dict[int, float] = {}  # strategy_id -> peak_equity
        self.last_reset: Dict[int, datetime] = {}  # strategy_id -> last_reset_time

    @log_performance("risk_management_latency")
    async def check_risk_limits(
        self,
        strategy_instance_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Tuple[bool, Optional[RiskViolation]]:
        """
        Check if strategy is within risk limits.

        Args:
            strategy_instance_id: Strategy instance ID
            user_id: User ID
            db: Database session

        Returns:
            Tuple of (is_within_limits, violation_if_any)
        """
        with PerformanceTracker(risk_management_histogram):
            try:
                # Get risk parameters
                risk_params = await self._get_risk_parameters(user_id, db)
                if not risk_params:
                    logger.warning(f"No risk parameters found for user {user_id}")
                    return True, None

                # Check daily loss limit
                violation = await self._check_daily_loss_limit(
                    strategy_instance_id,
                    risk_params,
                    db
                )
                if violation:
                    return False, violation

                # Check drawdown limit
                violation = await self._check_drawdown_limit(
                    strategy_instance_id,
                    risk_params,
                    db
                )
                if violation:
                    return False, violation

                return True, None

            except Exception as e:
                logger.error(f"Error checking risk limits: {e}", exc_info=True)
                return True, None  # Fail open to not block trading

    async def check_position_size_limit(
        self,
        strategy_instance_id: int,
        user_id: int,
        proposed_position_value: float,
        db: AsyncSession
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if proposed position size is within limits.

        Args:
            strategy_instance_id: Strategy instance ID
            user_id: User ID
            proposed_position_value: Value of proposed position
            db: Database session

        Returns:
            Tuple of (is_allowed, reason_if_not)
        """
        try:
            risk_params = await self._get_risk_parameters(user_id, db)
            if not risk_params:
                return True, None

            # Get strategy instance
            result = await db.execute(
                select(StrategyInstance)
                .where(StrategyInstance.id == strategy_instance_id)
            )
            instance = result.scalar_one_or_none()

            if not instance:
                return False, "Strategy instance not found"

            # Check against max position size
            if proposed_position_value > instance.max_position_size:
                return False, f"Position size {proposed_position_value} exceeds max {instance.max_position_size}"

            # Check current number of positions
            result = await db.execute(
                select(func.count(Position.id))
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.OPEN
                )
            )
            current_positions = result.scalar_one()

            if current_positions >= risk_params.max_positions_per_strategy:
                return False, f"Max positions limit {risk_params.max_positions_per_strategy} reached"

            return True, None

        except Exception as e:
            logger.error(f"Error checking position size limit: {e}", exc_info=True)
            return True, None  # Fail open

    async def calculate_daily_pnl(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> float:
        """
        Calculate total P&L for current trading day.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            Daily P&L
        """
        try:
            # Check if we need to reset cache (new trading day)
            await self._reset_daily_cache_if_needed(strategy_instance_id)

            # Get cached value if available
            if strategy_instance_id in self.daily_pnl_cache:
                return self.daily_pnl_cache[strategy_instance_id]

            # Calculate from database
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            # Get realized P&L from closed positions
            result = await db.execute(
                select(func.sum(Position.realized_pnl))
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.CLOSED,
                    Position.exit_time >= today_start
                )
            )
            realized_pnl = result.scalar_one_or_none() or 0.0

            # Get unrealized P&L from open positions
            result = await db.execute(
                select(func.sum(Position.unrealized_pnl))
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.OPEN
                )
            )
            unrealized_pnl = result.scalar_one_or_none() or 0.0

            daily_pnl = realized_pnl + unrealized_pnl

            # Cache the value
            self.daily_pnl_cache[strategy_instance_id] = daily_pnl

            return daily_pnl

        except Exception as e:
            logger.error(f"Error calculating daily P&L: {e}", exc_info=True)
            return 0.0

    async def calculate_drawdown(
        self,
        strategy_instance_id: int,
        current_equity: float,
        db: AsyncSession
    ) -> Tuple[float, float]:
        """
        Calculate current drawdown.

        Args:
            strategy_instance_id: Strategy instance ID
            current_equity: Current equity value
            db: Database session

        Returns:
            Tuple of (drawdown_amount, drawdown_percentage)
        """
        try:
            # Get or initialize peak equity
            if strategy_instance_id not in self.peak_equity_cache:
                # Get strategy instance to get initial capital
                result = await db.execute(
                    select(StrategyInstance)
                    .where(StrategyInstance.id == strategy_instance_id)
                )
                instance = result.scalar_one_or_none()
                if instance:
                    self.peak_equity_cache[strategy_instance_id] = instance.max_position_size

            peak_equity = self.peak_equity_cache.get(strategy_instance_id, current_equity)

            # Update peak if current equity is higher
            if current_equity > peak_equity:
                peak_equity = current_equity
                self.peak_equity_cache[strategy_instance_id] = peak_equity

            # Calculate drawdown
            if peak_equity == 0:
                return 0.0, 0.0

            drawdown_amount = peak_equity - current_equity
            drawdown_percentage = (drawdown_amount / peak_equity) * 100

            return drawdown_amount, drawdown_percentage

        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}", exc_info=True)
            return 0.0, 0.0

    async def close_all_positions(
        self,
        strategy_instance_id: int,
        reason: str,
        db: AsyncSession
    ) -> int:
        """
        Close all open positions for a strategy.

        Args:
            strategy_instance_id: Strategy instance ID
            reason: Reason for closing positions
            db: Database session

        Returns:
            Number of positions closed
        """
        try:
            # Get all open positions
            result = await db.execute(
                select(Position)
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.OPEN
                )
            )
            open_positions = result.scalars().all()

            closed_count = 0

            for position in open_positions:
                # Close position at current price
                position.exit_price = position.current_price
                position.exit_time = datetime.utcnow()
                position.status = PositionStatus.CLOSED

                # Calculate realized P&L
                if position.side == OrderSide.BUY:
                    pnl = (position.current_price - position.entry_price) * position.quantity
                else:
                    pnl = (position.entry_price - position.current_price) * position.quantity

                position.realized_pnl = pnl
                closed_count += 1

                log_risk_event(
                    event_type="position_auto_closed",
                    severity="warning",
                    details={
                        "position_id": position.id,
                        "symbol": position.symbol,
                        "reason": reason,
                        "pnl": pnl
                    }
                )

            await db.commit()

            logger.warning(
                f"Closed {closed_count} positions for strategy {strategy_instance_id}",
                strategy_id=strategy_instance_id,
                reason=reason
            )

            return closed_count

        except Exception as e:
            logger.error(f"Error closing positions: {e}", exc_info=True)
            await db.rollback()
            return 0

    async def _get_risk_parameters(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Optional[RiskParameters]:
        """Get risk parameters for user."""
        result = await db.execute(
            select(RiskParameters)
            .where(RiskParameters.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _check_daily_loss_limit(
        self,
        strategy_instance_id: int,
        risk_params: RiskParameters,
        db: AsyncSession
    ) -> Optional[RiskViolation]:
        """Check if daily loss limit is breached."""
        daily_pnl = await self.calculate_daily_pnl(strategy_instance_id, db)

        # Check percentage limit
        if risk_params.max_daily_loss_percentage:
            # Get strategy to calculate percentage
            result = await db.execute(
                select(StrategyInstance)
                .where(StrategyInstance.id == strategy_instance_id)
            )
            instance = result.scalar_one_or_none()

            if instance and instance.max_position_size > 0:
                loss_percentage = abs(daily_pnl / instance.max_position_size) * 100

                if daily_pnl < 0 and loss_percentage > risk_params.max_daily_loss_percentage:
                    risk_limit_breaches_counter.labels(limit_type="daily_loss_percentage").inc()

                    log_risk_event(
                        event_type="daily_loss_limit_breached",
                        severity="critical",
                        details={
                            "strategy_id": strategy_instance_id,
                            "daily_pnl": daily_pnl,
                            "loss_percentage": loss_percentage,
                            "limit": risk_params.max_daily_loss_percentage
                        }
                    )

                    return RiskViolation(
                        violation_type="daily_loss_percentage",
                        current_value=loss_percentage,
                        limit_value=risk_params.max_daily_loss_percentage,
                        severity="critical",
                        message=f"Daily loss {loss_percentage:.2f}% exceeds limit {risk_params.max_daily_loss_percentage}%"
                    )

        # Check absolute amount limit
        if risk_params.max_daily_loss_amount:
            if daily_pnl < 0 and abs(daily_pnl) > risk_params.max_daily_loss_amount:
                risk_limit_breaches_counter.labels(limit_type="daily_loss_amount").inc()

                log_risk_event(
                    event_type="daily_loss_amount_breached",
                    severity="critical",
                    details={
                        "strategy_id": strategy_instance_id,
                        "daily_pnl": daily_pnl,
                        "limit": risk_params.max_daily_loss_amount
                    }
                )

                return RiskViolation(
                    violation_type="daily_loss_amount",
                    current_value=abs(daily_pnl),
                    limit_value=risk_params.max_daily_loss_amount,
                    severity="critical",
                    message=f"Daily loss ${abs(daily_pnl):.2f} exceeds limit ${risk_params.max_daily_loss_amount:.2f}"
                )

        return None

    async def _check_drawdown_limit(
        self,
        strategy_instance_id: int,
        risk_params: RiskParameters,
        db: AsyncSession
    ) -> Optional[RiskViolation]:
        """Check if drawdown limit is breached."""
        # Get current equity (simplified - should be calculated properly)
        result = await db.execute(
            select(StrategyInstance)
            .where(StrategyInstance.id == strategy_instance_id)
        )
        instance = result.scalar_one_or_none()

        if not instance:
            return None

        current_equity = instance.max_position_size + instance.total_pnl

        drawdown_amount, drawdown_percentage = await self.calculate_drawdown(
            strategy_instance_id,
            current_equity,
            db
        )

        if drawdown_percentage > risk_params.max_drawdown_percentage:
            risk_limit_breaches_counter.labels(limit_type="drawdown").inc()

            log_risk_event(
                event_type="drawdown_limit_breached",
                severity="critical",
                details={
                    "strategy_id": strategy_instance_id,
                    "drawdown_percentage": drawdown_percentage,
                    "limit": risk_params.max_drawdown_percentage
                }
            )

            return RiskViolation(
                violation_type="drawdown",
                current_value=drawdown_percentage,
                limit_value=risk_params.max_drawdown_percentage,
                severity="critical",
                message=f"Drawdown {drawdown_percentage:.2f}% exceeds limit {risk_params.max_drawdown_percentage}%"
            )

        return None

    async def _reset_daily_cache_if_needed(self, strategy_instance_id: int) -> None:
        """Reset daily cache if it's a new trading day."""
        now = datetime.utcnow()
        last_reset = self.last_reset.get(strategy_instance_id)

        if not last_reset or last_reset.date() < now.date():
            # New trading day - reset cache
            self.daily_pnl_cache.pop(strategy_instance_id, None)
            self.last_reset[strategy_instance_id] = now


# Global risk manager instance
risk_manager = RiskManager()
