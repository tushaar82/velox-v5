"""
Performance analytics service.
Calculates and tracks trading performance metrics.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ...models.strategy import StrategyInstance
from ...models.trading import (
    Position, TradeOrder, PositionStatus, StrategyPerformance, PerformanceMetrics
)
from ...utils.logging import get_logger
import numpy as np


logger = get_logger(__name__)


class PerformanceAnalytics:
    """
    Calculates and tracks trading performance metrics.
    Provides real-time analytics for strategy performance.
    """

    async def calculate_strategy_performance(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> Dict:
        """
        Calculate comprehensive performance metrics for a strategy.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            Dictionary of performance metrics
        """
        try:
            # Get all closed positions
            result = await db.execute(
                select(Position)
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.CLOSED
                )
                .order_by(Position.exit_time)
            )
            closed_positions = result.scalars().all()

            # Get open positions
            result = await db.execute(
                select(Position)
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.OPEN
                )
            )
            open_positions = result.scalars().all()

            # Calculate metrics
            total_trades = len(closed_positions)
            winning_trades = len([p for p in closed_positions if p.realized_pnl > 0])
            losing_trades = len([p for p in closed_positions if p.realized_pnl < 0])

            realized_pnl = sum(p.realized_pnl for p in closed_positions)
            unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)
            total_pnl = realized_pnl + unrealized_pnl

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # Calculate average wins and losses
            wins = [p.realized_pnl for p in closed_positions if p.realized_pnl > 0]
            losses = [abs(p.realized_pnl) for p in closed_positions if p.realized_pnl < 0]

            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0

            # Profit factor
            total_wins = sum(wins) if wins else 0
            total_losses = sum(losses) if losses else 0
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

            # Get strategy instance for initial capital
            result = await db.execute(
                select(StrategyInstance)
                .where(StrategyInstance.id == strategy_instance_id)
            )
            instance = result.scalar_one_or_none()

            initial_capital = instance.max_position_size if instance else 10000
            current_equity = initial_capital + total_pnl

            # Return on investment
            roi_percentage = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

            # Calculate drawdown
            max_drawdown, max_drawdown_pct = await self._calculate_max_drawdown(
                closed_positions,
                initial_capital
            )

            # Calculate Sharpe ratio
            sharpe_ratio = await self._calculate_sharpe_ratio(closed_positions)

            # Calculate Sortino ratio
            sortino_ratio = await self._calculate_sortino_ratio(closed_positions)

            return {
                "strategy_instance_id": strategy_instance_id,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "realized_pnl": round(realized_pnl, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "total_pnl": round(total_pnl, 2),
                "average_win": round(avg_win, 2),
                "average_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2),
                "initial_capital": initial_capital,
                "current_equity": round(current_equity, 2),
                "roi_percentage": round(roi_percentage, 2),
                "max_drawdown": round(max_drawdown, 2),
                "max_drawdown_percentage": round(max_drawdown_pct, 2),
                "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio else None,
                "sortino_ratio": round(sortino_ratio, 2) if sortino_ratio else None,
                "open_positions": len(open_positions),
                "largest_win": round(max(wins), 2) if wins else 0,
                "largest_loss": round(max(losses), 2) if losses else 0,
            }

        except Exception as e:
            logger.error(f"Error calculating strategy performance: {e}", exc_info=True)
            return {}

    async def get_equity_curve(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Get equity curve data for charting.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            List of equity points
        """
        try:
            # Get strategy instance
            result = await db.execute(
                select(StrategyInstance)
                .where(StrategyInstance.id == strategy_instance_id)
            )
            instance = result.scalar_one_or_none()

            if not instance:
                return []

            initial_capital = instance.max_position_size

            # Get all closed positions in chronological order
            result = await db.execute(
                select(Position)
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.CLOSED
                )
                .order_by(Position.exit_time)
            )
            positions = result.scalars().all()

            equity_curve = []
            running_equity = initial_capital

            # Add starting point
            start_time = instance.started_at or datetime.utcnow()
            equity_curve.append({
                "timestamp": start_time.isoformat(),
                "equity": initial_capital,
                "pnl": 0
            })

            # Calculate equity after each trade
            for position in positions:
                running_equity += position.realized_pnl
                equity_curve.append({
                    "timestamp": position.exit_time.isoformat(),
                    "equity": round(running_equity, 2),
                    "pnl": round(position.realized_pnl, 2)
                })

            return equity_curve

        except Exception as e:
            logger.error(f"Error getting equity curve: {e}", exc_info=True)
            return []

    async def get_daily_pnl_chart(
        self,
        strategy_instance_id: int,
        days: int,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Get daily P&L for charting.

        Args:
            strategy_instance_id: Strategy instance ID
            days: Number of days to include
            db: Database session

        Returns:
            List of daily P&L data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Get all closed positions in the time range
            result = await db.execute(
                select(Position)
                .where(
                    Position.strategy_instance_id == strategy_instance_id,
                    Position.status == PositionStatus.CLOSED,
                    Position.exit_time >= start_date
                )
                .order_by(Position.exit_time)
            )
            positions = result.scalars().all()

            # Group by day
            daily_pnl = {}
            for position in positions:
                date_key = position.exit_time.date().isoformat()
                if date_key not in daily_pnl:
                    daily_pnl[date_key] = 0
                daily_pnl[date_key] += position.realized_pnl

            # Convert to list
            return [
                {
                    "date": date,
                    "pnl": round(pnl, 2)
                }
                for date, pnl in sorted(daily_pnl.items())
            ]

        except Exception as e:
            logger.error(f"Error getting daily P&L: {e}", exc_info=True)
            return []

    async def get_drawdown_chart(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Get drawdown data for charting.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            List of drawdown points
        """
        try:
            # Get equity curve first
            equity_curve = await self.get_equity_curve(strategy_instance_id, db)

            if not equity_curve:
                return []

            drawdown_data = []
            peak_equity = equity_curve[0]["equity"]

            for point in equity_curve:
                current_equity = point["equity"]

                # Update peak
                if current_equity > peak_equity:
                    peak_equity = current_equity

                # Calculate drawdown
                drawdown = peak_equity - current_equity
                drawdown_pct = (drawdown / peak_equity * 100) if peak_equity > 0 else 0

                drawdown_data.append({
                    "timestamp": point["timestamp"],
                    "drawdown": round(drawdown, 2),
                    "drawdown_percentage": round(drawdown_pct, 2),
                    "peak_equity": round(peak_equity, 2)
                })

            return drawdown_data

        except Exception as e:
            logger.error(f"Error getting drawdown chart: {e}", exc_info=True)
            return []

    async def save_performance_snapshot(
        self,
        strategy_instance_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Save a performance metrics snapshot.

        Args:
            strategy_instance_id: Strategy instance ID
            db: Database session

        Returns:
            True if successful
        """
        try:
            # Calculate current metrics
            metrics = await self.calculate_strategy_performance(strategy_instance_id, db)

            if not metrics:
                return False

            # Get strategy instance
            result = await db.execute(
                select(StrategyInstance)
                .where(StrategyInstance.id == strategy_instance_id)
            )
            instance = result.scalar_one_or_none()

            if not instance:
                return False

            # Create snapshot
            snapshot = PerformanceMetrics(
                strategy_instance_id=strategy_instance_id,
                snapshot_time=datetime.utcnow(),
                equity=metrics["current_equity"],
                cash=instance.max_position_size - metrics["unrealized_pnl"],
                realized_pnl=metrics["realized_pnl"],
                unrealized_pnl=metrics["unrealized_pnl"],
                total_pnl=metrics["total_pnl"],
                open_positions_count=metrics["open_positions"],
                open_positions_value=metrics["unrealized_pnl"],
                drawdown=metrics["max_drawdown"],
                drawdown_percentage=metrics["max_drawdown_percentage"]
            )

            db.add(snapshot)
            await db.commit()

            return True

        except Exception as e:
            logger.error(f"Error saving performance snapshot: {e}", exc_info=True)
            await db.rollback()
            return False

    async def _calculate_max_drawdown(
        self,
        positions: List[Position],
        initial_capital: float
    ) -> tuple[float, float]:
        """Calculate maximum drawdown from positions."""
        if not positions:
            return 0.0, 0.0

        equity = initial_capital
        peak_equity = initial_capital
        max_drawdown = 0.0

        for position in positions:
            equity += position.realized_pnl

            if equity > peak_equity:
                peak_equity = equity

            drawdown = peak_equity - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_pct = (max_drawdown / peak_equity * 100) if peak_equity > 0 else 0
        return max_drawdown, max_drawdown_pct

    async def _calculate_sharpe_ratio(
        self,
        positions: List[Position],
        risk_free_rate: float = 0.02
    ) -> Optional[float]:
        """Calculate Sharpe ratio."""
        if len(positions) < 2:
            return None

        returns = [p.realized_pnl for p in positions]

        if not returns:
            return None

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return None

        # Annualized Sharpe ratio (assuming 252 trading days)
        sharpe = (avg_return - risk_free_rate / 252) / std_return * np.sqrt(252)
        return float(sharpe)

    async def _calculate_sortino_ratio(
        self,
        positions: List[Position],
        risk_free_rate: float = 0.02
    ) -> Optional[float]:
        """Calculate Sortino ratio (only considers downside deviation)."""
        if len(positions) < 2:
            return None

        returns = [p.realized_pnl for p in positions]

        if not returns:
            return None

        avg_return = np.mean(returns)

        # Downside deviation (only negative returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return None

        downside_std = np.std(downside_returns)

        if downside_std == 0:
            return None

        # Annualized Sortino ratio
        sortino = (avg_return - risk_free_rate / 252) / downside_std * np.sqrt(252)
        return float(sortino)


# Global performance analytics instance
performance_analytics = PerformanceAnalytics()
