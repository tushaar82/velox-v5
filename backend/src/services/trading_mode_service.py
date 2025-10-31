"""
Trading mode service.
Manages live and paper trading modes for strategy instances.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.strategy import StrategyInstance, TradingMode
from ...models.user import PaperTradingAccount
from ...models.trading import Position, TradeOrder, PositionStatus
from ...utils.logging import get_logger, log_trading_mode_event


logger = get_logger(__name__)


class TradingModeService:
    """
    Manages trading modes (live vs paper trading).
    Ensures safe switching between modes with proper confirmations.
    """

    async def switch_mode(
        self,
        strategy_instance_id: int,
        new_mode: TradingMode,
        user_id: int,
        force: bool,
        db: AsyncSession
    ) -> tuple[bool, Optional[str]]:
        """
        Switch trading mode for a strategy instance.

        Args:
            strategy_instance_id: Strategy instance ID
            new_mode: New trading mode (LIVE or PAPER)
            user_id: User ID
            force: Force switch even if positions are open
            db: Database session

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get strategy instance
            result = await db.execute(
                select(StrategyInstance)
                .where(
                    StrategyInstance.id == strategy_instance_id,
                    StrategyInstance.user_id == user_id
                )
            )
            instance = result.scalar_one_or_none()

            if not instance:
                return False, "Strategy instance not found"

            old_mode = instance.trading_mode

            # Check if already in the requested mode
            if old_mode == new_mode:
                return False, f"Strategy is already in {new_mode.value} mode"

            # Check for open positions if not forced
            if not force:
                result = await db.execute(
                    select(Position)
                    .where(
                        Position.strategy_instance_id == strategy_instance_id,
                        Position.status == PositionStatus.OPEN
                    )
                )
                open_positions = result.scalars().all()

                if open_positions:
                    return False, (
                        f"Cannot switch mode with {len(open_positions)} open positions. "
                        "Close all positions first or use force=true"
                    )

            # Ensure paper trading account exists for paper mode
            if new_mode == TradingMode.PAPER:
                paper_account = await self._ensure_paper_account(user_id, db)
                if not paper_account:
                    return False, "Failed to create paper trading account"

            # Update trading mode
            instance.trading_mode = new_mode
            await db.commit()

            # Log mode change
            log_trading_mode_event(
                strategy_id=str(strategy_instance_id),
                old_mode=old_mode.value,
                new_mode=new_mode.value,
                user_id=str(user_id)
            )

            logger.info(
                f"Trading mode switched from {old_mode.value} to {new_mode.value}",
                strategy_id=strategy_instance_id,
                user_id=user_id
            )

            return True, None

        except Exception as e:
            logger.error(f"Error switching trading mode: {e}", exc_info=True)
            await db.rollback()
            return False, str(e)

    async def execute_paper_trade(
        self,
        order: TradeOrder,
        fill_price: float,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Execute trade in paper trading mode.

        Args:
            order: Trade order
            fill_price: Simulated fill price
            user_id: User ID
            db: Database session

        Returns:
            True if successful
        """
        try:
            # Get paper trading account
            paper_account = await self._get_paper_account(user_id, db)
            if not paper_account:
                logger.error(f"Paper trading account not found for user {user_id}")
                return False

            # Calculate trade value
            trade_value = fill_price * order.quantity

            # Check if sufficient balance (for buys)
            if order.side.value == "buy":
                if paper_account.current_balance < trade_value:
                    logger.warning(
                        f"Insufficient paper trading balance: {paper_account.current_balance} < {trade_value}"
                    )
                    return False

                # Deduct from balance
                paper_account.current_balance -= trade_value

            else:  # sell
                # Add to balance
                paper_account.current_balance += trade_value

            await db.commit()

            logger.info(
                f"Paper trade executed: {order.side.value} {order.quantity} @ {fill_price}",
                order_id=order.id,
                new_balance=paper_account.current_balance
            )

            return True

        except Exception as e:
            logger.error(f"Error executing paper trade: {e}", exc_info=True)
            await db.rollback()
            return False

    async def close_paper_position(
        self,
        position: Position,
        exit_price: float,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Close position in paper trading mode.

        Args:
            position: Position to close
            exit_price: Exit price
            user_id: User ID
            db: Database session

        Returns:
            True if successful
        """
        try:
            # Get paper trading account
            paper_account = await self._get_paper_account(user_id, db)
            if not paper_account:
                return False

            # Calculate P&L
            if position.side.value == "buy":
                pnl = (exit_price - position.entry_price) * position.quantity
                # Return initial investment + P&L
                paper_account.current_balance += (position.entry_price * position.quantity) + pnl
            else:  # short
                pnl = (position.entry_price - exit_price) * position.quantity
                # Return margin + P&L
                paper_account.current_balance += (position.entry_price * position.quantity) + pnl

            # Update total P&L
            paper_account.total_pnl += pnl

            await db.commit()

            logger.info(
                f"Paper position closed with P&L: {pnl}",
                position_id=position.id,
                pnl=pnl,
                new_balance=paper_account.current_balance
            )

            return True

        except Exception as e:
            logger.error(f"Error closing paper position: {e}", exc_info=True)
            await db.rollback()
            return False

    async def get_paper_account_balance(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Optional[dict]:
        """
        Get paper trading account balance.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Balance information or None
        """
        paper_account = await self._get_paper_account(user_id, db)
        if not paper_account:
            return None

        return {
            "current_balance": paper_account.current_balance,
            "initial_balance": paper_account.initial_balance,
            "total_pnl": paper_account.total_pnl,
            "return_percentage": (
                (paper_account.total_pnl / paper_account.initial_balance) * 100
                if paper_account.initial_balance > 0
                else 0
            )
        }

    async def reset_paper_account(
        self,
        user_id: int,
        new_balance: Optional[float],
        db: AsyncSession
    ) -> bool:
        """
        Reset paper trading account.

        Args:
            user_id: User ID
            new_balance: New starting balance (optional)
            db: Database session

        Returns:
            True if successful
        """
        try:
            paper_account = await self._get_paper_account(user_id, db)
            if not paper_account:
                return False

            reset_balance = new_balance if new_balance else paper_account.initial_balance

            paper_account.current_balance = reset_balance
            paper_account.initial_balance = reset_balance
            paper_account.total_pnl = 0.0

            await db.commit()

            logger.info(
                f"Paper trading account reset to {reset_balance}",
                user_id=user_id
            )

            return True

        except Exception as e:
            logger.error(f"Error resetting paper account: {e}", exc_info=True)
            await db.rollback()
            return False

    async def _ensure_paper_account(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Optional[PaperTradingAccount]:
        """
        Ensure paper trading account exists for user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Paper trading account
        """
        # Check if account exists
        paper_account = await self._get_paper_account(user_id, db)

        if not paper_account:
            # Create new paper trading account
            paper_account = PaperTradingAccount(
                user_id=user_id,
                initial_balance=100000.0,  # Default starting balance
                current_balance=100000.0,
                total_pnl=0.0
            )
            db.add(paper_account)
            await db.commit()
            await db.refresh(paper_account)

            logger.info(
                f"Paper trading account created for user {user_id}",
                initial_balance=100000.0
            )

        return paper_account

    async def _get_paper_account(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Optional[PaperTradingAccount]:
        """Get paper trading account for user."""
        result = await db.execute(
            select(PaperTradingAccount)
            .where(PaperTradingAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()


# Global trading mode service instance
trading_mode_service = TradingModeService()
