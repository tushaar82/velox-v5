"""
Analytics API endpoints.
Provides performance analytics and metrics for strategies.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from ...models.database import get_db
from ...models.user import User
from ...models.strategy import StrategyInstance
from ...core.security import get_current_active_user
from ...services.analytics.performance import performance_analytics


router = APIRouter()


# Pydantic schemas
class PerformanceMetrics(BaseModel):
    """Performance metrics response."""
    strategy_instance_id: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float
    initial_capital: float
    current_equity: float
    roi_percentage: float
    max_drawdown: float
    max_drawdown_percentage: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    open_positions: int
    largest_win: float
    largest_loss: float


class EquityPoint(BaseModel):
    """Equity curve data point."""
    timestamp: str
    equity: float
    pnl: float


class DailyPnLPoint(BaseModel):
    """Daily P&L data point."""
    date: str
    pnl: float


class DrawdownPoint(BaseModel):
    """Drawdown data point."""
    timestamp: str
    drawdown: float
    drawdown_percentage: float
    peak_equity: float


@router.get("/performance/{strategy_instance_id}", response_model=PerformanceMetrics)
async def get_strategy_performance(
    strategy_instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive performance metrics for a strategy."""
    # Verify strategy belongs to user
    result = await db.execute(
        select(StrategyInstance)
        .where(
            StrategyInstance.id == strategy_instance_id,
            StrategyInstance.user_id == current_user.id
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=404,
            detail="Strategy instance not found"
        )

    # Calculate performance
    metrics = await performance_analytics.calculate_strategy_performance(
        strategy_instance_id,
        db
    )

    if not metrics:
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate performance metrics"
        )

    return PerformanceMetrics(**metrics)


@router.get("/equity-curve/{strategy_instance_id}", response_model=List[EquityPoint])
async def get_equity_curve(
    strategy_instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get equity curve data for charting."""
    # Verify strategy belongs to user
    result = await db.execute(
        select(StrategyInstance)
        .where(
            StrategyInstance.id == strategy_instance_id,
            StrategyInstance.user_id == current_user.id
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=404,
            detail="Strategy instance not found"
        )

    # Get equity curve
    equity_data = await performance_analytics.get_equity_curve(
        strategy_instance_id,
        db
    )

    return [EquityPoint(**point) for point in equity_data]


@router.get("/daily-pnl/{strategy_instance_id}", response_model=List[DailyPnLPoint])
async def get_daily_pnl(
    strategy_instance_id: int,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily P&L data for charting."""
    # Verify strategy belongs to user
    result = await db.execute(
        select(StrategyInstance)
        .where(
            StrategyInstance.id == strategy_instance_id,
            StrategyInstance.user_id == current_user.id
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=404,
            detail="Strategy instance not found"
        )

    # Get daily P&L
    pnl_data = await performance_analytics.get_daily_pnl_chart(
        strategy_instance_id,
        days,
        db
    )

    return [DailyPnLPoint(**point) for point in pnl_data]


@router.get("/drawdown/{strategy_instance_id}", response_model=List[DrawdownPoint])
async def get_drawdown_chart(
    strategy_instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get drawdown data for charting."""
    # Verify strategy belongs to user
    result = await db.execute(
        select(StrategyInstance)
        .where(
            StrategyInstance.id == strategy_instance_id,
            StrategyInstance.user_id == current_user.id
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=404,
            detail="Strategy instance not found"
        )

    # Get drawdown data
    drawdown_data = await performance_analytics.get_drawdown_chart(
        strategy_instance_id,
        db
    )

    return [DrawdownPoint(**point) for point in drawdown_data]


@router.post("/snapshot/{strategy_instance_id}")
async def save_performance_snapshot(
    strategy_instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Save a performance metrics snapshot."""
    # Verify strategy belongs to user
    result = await db.execute(
        select(StrategyInstance)
        .where(
            StrategyInstance.id == strategy_instance_id,
            StrategyInstance.user_id == current_user.id
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=404,
            detail="Strategy instance not found"
        )

    # Save snapshot
    success = await performance_analytics.save_performance_snapshot(
        strategy_instance_id,
        db
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to save performance snapshot"
        )

    return {"message": "Performance snapshot saved", "strategy_instance_id": strategy_instance_id}
