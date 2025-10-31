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
from ...models.strategy import StrategyInstance, BacktestResult, Strategy
from ...core.security import get_current_active_user
from ...services.analytics.performance import performance_analytics
from ...services.analytics.backtesting import backtest_engine
from ...services.strategy_engine.momentum_strategy import MomentumStrategy
from datetime import datetime


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


# Backtest schemas
class BacktestRequest(BaseModel):
    """Backtest request."""
    strategy_id: int
    symbol: str
    start_date: str  # ISO format
    end_date: str    # ISO format
    initial_capital: float = 100000.0
    name: str | None = None


class BacktestResultResponse(BaseModel):
    """Backtest result response."""
    id: int
    strategy_id: int
    name: str
    start_date: str
    end_date: str
    symbols: List[str]
    initial_capital: float
    total_return: float
    total_return_percentage: float
    annualized_return: float
    max_drawdown: float
    max_drawdown_percentage: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None
    created_at: str


@router.post("/backtest", response_model=BacktestResultResponse)
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a backtest for a strategy.
    """
    # Verify strategy exists and belongs to user
    result = await db.execute(
        select(Strategy)
        .where(Strategy.id == request.strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=404,
            detail="Strategy not found"
        )

    # Parse dates
    try:
        start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {str(e)}"
        )

    # Validate date range
    if start_date >= end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )

    # For demo, we'll use MomentumStrategy
    # In production, this would dynamically load the strategy based on strategy_id
    strategy_engine = MomentumStrategy(strategy.parameters or {})

    try:
        # Run backtest
        backtest_result = await backtest_engine.run_backtest(
            strategy_engine=strategy_engine,
            strategy_id=request.strategy_id,
            user_id=current_user.id,
            symbol=request.symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=request.initial_capital,
            db=db,
            name=request.name
        )

        return BacktestResultResponse(
            id=backtest_result.id,
            strategy_id=backtest_result.strategy_id,
            name=backtest_result.name,
            start_date=backtest_result.start_date.isoformat(),
            end_date=backtest_result.end_date.isoformat(),
            symbols=backtest_result.symbols,
            initial_capital=backtest_result.initial_capital,
            total_return=backtest_result.total_return,
            total_return_percentage=backtest_result.total_return_percentage,
            annualized_return=backtest_result.annualized_return,
            max_drawdown=backtest_result.max_drawdown,
            max_drawdown_percentage=backtest_result.max_drawdown_percentage,
            total_trades=backtest_result.total_trades,
            winning_trades=backtest_result.winning_trades,
            losing_trades=backtest_result.losing_trades,
            win_rate=backtest_result.win_rate,
            sharpe_ratio=backtest_result.sharpe_ratio,
            sortino_ratio=backtest_result.sortino_ratio,
            calmar_ratio=backtest_result.calmar_ratio,
            created_at=backtest_result.created_at.isoformat()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {str(e)}"
        )


@router.get("/backtest/{backtest_id}", response_model=BacktestResultResponse)
async def get_backtest_result(
    backtest_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific backtest result."""
    result = await db.execute(
        select(BacktestResult)
        .where(
            BacktestResult.id == backtest_id,
            BacktestResult.user_id == current_user.id
        )
    )
    backtest_result = result.scalar_one_or_none()

    if not backtest_result:
        raise HTTPException(
            status_code=404,
            detail="Backtest result not found"
        )

    return BacktestResultResponse(
        id=backtest_result.id,
        strategy_id=backtest_result.strategy_id,
        name=backtest_result.name,
        start_date=backtest_result.start_date.isoformat(),
        end_date=backtest_result.end_date.isoformat(),
        symbols=backtest_result.symbols,
        initial_capital=backtest_result.initial_capital,
        total_return=backtest_result.total_return,
        total_return_percentage=backtest_result.total_return_percentage,
        annualized_return=backtest_result.annualized_return,
        max_drawdown=backtest_result.max_drawdown,
        max_drawdown_percentage=backtest_result.max_drawdown_percentage,
        total_trades=backtest_result.total_trades,
        winning_trades=backtest_result.winning_trades,
        losing_trades=backtest_result.losing_trades,
        win_rate=backtest_result.win_rate,
        sharpe_ratio=backtest_result.sharpe_ratio,
        sortino_ratio=backtest_result.sortino_ratio,
        calmar_ratio=backtest_result.calmar_ratio,
        created_at=backtest_result.created_at.isoformat()
    )


@router.get("/backtest/strategy/{strategy_id}", response_model=List[BacktestResultResponse])
async def list_backtest_results(
    strategy_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all backtest results for a strategy."""
    result = await db.execute(
        select(BacktestResult)
        .where(
            BacktestResult.strategy_id == strategy_id,
            BacktestResult.user_id == current_user.id
        )
        .order_by(BacktestResult.created_at.desc())
    )
    backtest_results = result.scalars().all()

    return [
        BacktestResultResponse(
            id=br.id,
            strategy_id=br.strategy_id,
            name=br.name,
            start_date=br.start_date.isoformat(),
            end_date=br.end_date.isoformat(),
            symbols=br.symbols,
            initial_capital=br.initial_capital,
            total_return=br.total_return,
            total_return_percentage=br.total_return_percentage,
            annualized_return=br.annualized_return,
            max_drawdown=br.max_drawdown,
            max_drawdown_percentage=br.max_drawdown_percentage,
            total_trades=br.total_trades,
            winning_trades=br.winning_trades,
            losing_trades=br.losing_trades,
            win_rate=br.win_rate,
            sharpe_ratio=br.sharpe_ratio,
            sortino_ratio=br.sortino_ratio,
            calmar_ratio=br.calmar_ratio,
            created_at=br.created_at.isoformat()
        )
        for br in backtest_results
    ]
