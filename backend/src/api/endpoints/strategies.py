"""
Strategy API endpoints.
Manages trading strategies and their instances.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from ...models.database import get_db
from ...models.user import User
from ...models.strategy import Strategy, StrategyInstance, StrategyStatus, TradingMode
from ...core.security import get_current_active_user
from ...services.strategy_engine.executor import strategy_executor
from ...services.trading_mode_service import trading_mode_service


router = APIRouter()


# Pydantic schemas
class StrategyCreate(BaseModel):
    """Create strategy request."""
    name: str
    description: str | None = None
    strategy_type: str
    parameters: dict = {}


class StrategyInstanceCreate(BaseModel):
    """Create strategy instance request."""
    strategy_id: int
    name: str
    symbols: List[str]
    trading_mode: str = "paper"
    parameters: dict = {}


class StrategyResponse(BaseModel):
    """Strategy response."""
    id: int
    name: str
    description: str | None
    strategy_type: str
    is_active: bool

    class Config:
        from_attributes = True


class StrategyInstanceResponse(BaseModel):
    """Strategy instance response."""
    id: int
    strategy_id: int
    name: str
    status: str
    trading_mode: str
    symbols: List[str]
    total_pnl: float
    total_trades: int

    class Config:
        from_attributes = True


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new strategy."""
    strategy = Strategy(
        user_id=current_user.id,
        name=strategy_data.name,
        description=strategy_data.description,
        strategy_type=strategy_data.strategy_type,
        parameters=strategy_data.parameters
    )

    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    return strategy


@router.get("/", response_model=List[StrategyResponse])
async def get_strategies(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's strategies."""
    result = await db.execute(
        select(Strategy)
        .where(Strategy.user_id == current_user.id)
        .order_by(Strategy.created_at.desc())
    )
    strategies = result.scalars().all()

    return strategies


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific strategy."""
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    return strategy


@router.post("/instances", response_model=StrategyInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy_instance(
    instance_data: StrategyInstanceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new strategy instance."""
    # Verify strategy exists and belongs to user
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == instance_data.strategy_id,
            Strategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    # Create instance
    instance = StrategyInstance(
        strategy_id=instance_data.strategy_id,
        user_id=current_user.id,
        name=instance_data.name,
        symbols=instance_data.symbols,
        trading_mode=TradingMode(instance_data.trading_mode),
        parameters=instance_data.parameters,
        status=StrategyStatus.STOPPED
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return instance


@router.get("/instances", response_model=List[StrategyInstanceResponse])
async def get_strategy_instances(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's strategy instances."""
    result = await db.execute(
        select(StrategyInstance)
        .where(StrategyInstance.user_id == current_user.id)
        .order_by(StrategyInstance.created_at.desc())
    )
    instances = result.scalars().all()

    return instances


@router.post("/instances/{instance_id}/start")
async def start_strategy_instance(
    instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a strategy instance."""
    result = await db.execute(
        select(StrategyInstance).where(
            StrategyInstance.id == instance_id,
            StrategyInstance.user_id == current_user.id
        )
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy instance not found"
        )

    # TODO: Initialize strategy engine based on strategy type
    # For now, just update status
    instance.status = StrategyStatus.ACTIVE
    instance.started_at = datetime.utcnow()
    await db.commit()

    return {"message": "Strategy started", "instance_id": instance_id}


@router.post("/instances/{instance_id}/stop")
async def stop_strategy_instance(
    instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Stop a strategy instance."""
    success = await strategy_executor.stop_strategy(instance_id, db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop strategy"
        )

    return {"message": "Strategy stopped", "instance_id": instance_id}


# Trading Mode Endpoints

class TradingModeSwitch(BaseModel):
    """Switch trading mode request."""
    mode: str  # "live" or "paper"
    force: bool = False


class PaperAccountResponse(BaseModel):
    """Paper trading account response."""
    current_balance: float
    initial_balance: float
    total_pnl: float
    return_percentage: float


@router.post("/instances/{instance_id}/switch-mode")
async def switch_trading_mode(
    instance_id: int,
    mode_switch: TradingModeSwitch,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Switch trading mode for a strategy instance."""
    # Validate mode
    try:
        new_mode = TradingMode(mode_switch.mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trading mode: {mode_switch.mode}. Must be 'live' or 'paper'"
        )

    # Switch mode
    success, error = await trading_mode_service.switch_mode(
        instance_id,
        new_mode,
        current_user.id,
        mode_switch.force,
        db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return {
        "message": f"Trading mode switched to {new_mode.value}",
        "instance_id": instance_id,
        "mode": new_mode.value
    }


@router.get("/paper-account", response_model=PaperAccountResponse)
async def get_paper_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get paper trading account balance."""
    balance_info = await trading_mode_service.get_paper_account_balance(
        current_user.id,
        db
    )

    if not balance_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper trading account not found"
        )

    return PaperAccountResponse(**balance_info)


@router.post("/paper-account/reset")
async def reset_paper_account(
    new_balance: float | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset paper trading account."""
    success = await trading_mode_service.reset_paper_account(
        current_user.id,
        new_balance,
        db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset paper trading account"
        )

    return {
        "message": "Paper trading account reset successfully",
        "new_balance": new_balance
    }
