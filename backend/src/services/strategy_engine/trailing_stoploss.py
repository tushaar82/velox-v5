"""
Trailing stoploss service.
Manages trailing stoploss orders for active positions.
"""
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.trading import Position, TrailingStoploss, PositionStatus, OrderSide
from ...utils.logging import get_logger, log_trailing_stoploss_event


logger = get_logger(__name__)


class TrailingStoplossService:
    """
    Manages trailing stoploss for positions.
    Automatically adjusts stoploss as price moves in favorable direction.
    """

    def __init__(self):
        """Initialize trailing stoploss service."""
        self.active_stoplosses: Dict[int, TrailingStoploss] = {}  # position_id -> stoploss

    async def create_trailing_stoploss(
        self,
        position: Position,
        trailing_percentage: float,
        trailing_amount: Optional[float],
        db: AsyncSession
    ) -> TrailingStoploss:
        """
        Create a trailing stoploss for a position.

        Args:
            position: Position to protect
            trailing_percentage: Trailing percentage (e.g., 2.0 for 2%)
            trailing_amount: Optional fixed trailing amount
            db: Database session

        Returns:
            Created trailing stoploss
        """
        try:
            # Calculate initial stop price
            if position.side == OrderSide.BUY:
                # For long positions, stoploss is below current price
                if trailing_amount:
                    stop_price = position.current_price - trailing_amount
                else:
                    stop_price = position.current_price * (1 - trailing_percentage / 100)
            else:
                # For short positions, stoploss is above current price
                if trailing_amount:
                    stop_price = position.current_price + trailing_amount
                else:
                    stop_price = position.current_price * (1 + trailing_percentage / 100)

            # Create trailing stoploss
            stoploss = TrailingStoploss(
                position_id=position.id,
                trailing_percentage=trailing_percentage,
                trailing_amount=trailing_amount,
                highest_price=position.current_price,
                current_stop_price=stop_price,
                is_active=True,
                is_triggered=False
            )

            db.add(stoploss)
            await db.commit()
            await db.refresh(stoploss)

            # Add to active stoplosses
            self.active_stoplosses[position.id] = stoploss

            log_trailing_stoploss_event(
                position_id=str(position.id),
                event="created",
                details={
                    "symbol": position.symbol,
                    "trailing_percentage": trailing_percentage,
                    "initial_stop_price": stop_price
                }
            )

            logger.info(
                f"Trailing stoploss created for position {position.id}",
                position_id=position.id,
                stop_price=stop_price
            )

            return stoploss

        except Exception as e:
            logger.error(f"Error creating trailing stoploss: {e}", exc_info=True)
            await db.rollback()
            raise

    async def update_trailing_stoploss(
        self,
        position: Position,
        current_price: float,
        db: AsyncSession
    ) -> Optional[bool]:
        """
        Update trailing stoploss based on current price.

        Args:
            position: Position with trailing stoploss
            current_price: Current market price
            db: Database session

        Returns:
            True if stoploss was triggered, False if updated, None if no stoploss
        """
        try:
            # Get trailing stoploss
            result = await db.execute(
                select(TrailingStoploss)
                .where(
                    TrailingStoploss.position_id == position.id,
                    TrailingStoploss.is_active == True
                )
            )
            stoploss = result.scalar_one_or_none()

            if not stoploss:
                return None

            # Check if stoploss is triggered
            is_triggered = self._check_trigger(position.side, current_price, stoploss.current_stop_price)

            if is_triggered:
                stoploss.is_triggered = True
                stoploss.is_active = False
                stoploss.triggered_at = datetime.utcnow()
                await db.commit()

                log_trailing_stoploss_event(
                    position_id=str(position.id),
                    event="triggered",
                    details={
                        "symbol": position.symbol,
                        "trigger_price": current_price,
                        "stop_price": stoploss.current_stop_price
                    }
                )

                logger.warning(
                    f"Trailing stoploss triggered for position {position.id}",
                    position_id=position.id,
                    trigger_price=current_price
                )

                return True

            # Update stoploss if price moved favorably
            updated = await self._adjust_stoploss(
                stoploss,
                position.side,
                current_price,
                db
            )

            if updated:
                await db.commit()

            return False

        except Exception as e:
            logger.error(f"Error updating trailing stoploss: {e}", exc_info=True)
            return None

    async def _adjust_stoploss(
        self,
        stoploss: TrailingStoploss,
        position_side: OrderSide,
        current_price: float,
        db: AsyncSession
    ) -> bool:
        """
        Adjust stoploss if price moved favorably.

        Args:
            stoploss: Trailing stoploss to adjust
            position_side: Position side (BUY/SELL)
            current_price: Current market price
            db: Database session

        Returns:
            True if stoploss was adjusted
        """
        adjusted = False

        if position_side == OrderSide.BUY:
            # For long positions, update if price went higher
            if current_price > stoploss.highest_price:
                old_stop = stoploss.current_stop_price
                stoploss.highest_price = current_price

                # Calculate new stop price
                if stoploss.trailing_amount:
                    new_stop = current_price - stoploss.trailing_amount
                else:
                    new_stop = current_price * (1 - stoploss.trailing_percentage / 100)

                # Only update if new stop is higher than old stop
                if new_stop > stoploss.current_stop_price:
                    stoploss.current_stop_price = new_stop
                    adjusted = True

                    log_trailing_stoploss_event(
                        position_id=str(stoploss.position_id),
                        event="adjusted",
                        details={
                            "old_stop": old_stop,
                            "new_stop": new_stop,
                            "highest_price": current_price
                        }
                    )

        else:  # Short position
            # For short positions, update if price went lower
            if current_price < stoploss.highest_price:
                old_stop = stoploss.current_stop_price
                stoploss.highest_price = current_price

                # Calculate new stop price
                if stoploss.trailing_amount:
                    new_stop = current_price + stoploss.trailing_amount
                else:
                    new_stop = current_price * (1 + stoploss.trailing_percentage / 100)

                # Only update if new stop is lower than old stop
                if new_stop < stoploss.current_stop_price:
                    stoploss.current_stop_price = new_stop
                    adjusted = True

                    log_trailing_stoploss_event(
                        position_id=str(stoploss.position_id),
                        event="adjusted",
                        details={
                            "old_stop": old_stop,
                            "new_stop": new_stop,
                            "highest_price": current_price
                        }
                    )

        return adjusted

    def _check_trigger(
        self,
        position_side: OrderSide,
        current_price: float,
        stop_price: float
    ) -> bool:
        """
        Check if stoploss is triggered.

        Args:
            position_side: Position side (BUY/SELL)
            current_price: Current market price
            stop_price: Stop loss price

        Returns:
            True if triggered
        """
        if position_side == OrderSide.BUY:
            # Long position: triggered if price falls below stop
            return current_price <= stop_price
        else:
            # Short position: triggered if price rises above stop
            return current_price >= stop_price

    async def deactivate_trailing_stoploss(
        self,
        position_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Deactivate trailing stoploss for a position.

        Args:
            position_id: Position ID
            db: Database session

        Returns:
            True if deactivated successfully
        """
        try:
            result = await db.execute(
                select(TrailingStoploss)
                .where(
                    TrailingStoploss.position_id == position_id,
                    TrailingStoploss.is_active == True
                )
            )
            stoploss = result.scalar_one_or_none()

            if stoploss:
                stoploss.is_active = False
                await db.commit()

                # Remove from active stoplosses
                self.active_stoplosses.pop(position_id, None)

                log_trailing_stoploss_event(
                    position_id=str(position_id),
                    event="deactivated",
                    details={}
                )

                logger.info(f"Trailing stoploss deactivated for position {position_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deactivating trailing stoploss: {e}", exc_info=True)
            await db.rollback()
            return False

    async def get_active_stoplosses(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> list[TrailingStoploss]:
        """
        Get all active trailing stoplosses for a strategy.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            List of active trailing stoplosses
        """
        result = await db.execute(
            select(TrailingStoploss)
            .join(Position)
            .where(
                Position.strategy_instance_id == strategy_instance_id,
                Position.status == PositionStatus.OPEN,
                TrailingStoploss.is_active == True
            )
        )
        return list(result.scalars().all())


# Global trailing stoploss service instance
trailing_stoploss_service = TrailingStoplossService()
