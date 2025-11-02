"""Strategy management API endpoints."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_current_active_user
from src.models.database import get_db
from src.models.strategy import StrategyInstance, StrategyStatus, TradingMode
from src.models.user import User
from src.services.strategy_engine.executor import strategy_executor
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class StrategyCreate(BaseModel):
    """Strategy creation request."""

    name: str
    description: str | None = None
    strategy_code: str
    parameters: dict
    symbols: List[str]
    timeframe: str
    trading_mode: TradingMode = TradingMode.PAPER
    max_positions: int = 5
    position_size: float


class StrategyResponse(BaseModel):
    """Strategy response."""

    id: str
    name: str
    description: str | None
    status: StrategyStatus
    trading_mode: TradingMode
    symbols: List[str]
    timeframe: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new trading strategy."""
    try:
        strategy = StrategyInstance(
            user_id=current_user.id,
            name=strategy_data.name,
            description=strategy_data.description,
            strategy_code=strategy_data.strategy_code,
            parameters=strategy_data.parameters,
            symbols=strategy_data.symbols,
            timeframe=strategy_data.timeframe,
            trading_mode=strategy_data.trading_mode,
            max_positions=strategy_data.max_positions,
            position_size=strategy_data.position_size,
            status=StrategyStatus.PAUSED,
        )

        db.add(strategy)
        await db.commit()
        await db.refresh(strategy)

        logger.info("strategy_created", strategy_id=str(strategy.id), user_id=str(current_user.id))

        return StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            description=strategy.description,
            status=strategy.status,
            trading_mode=strategy.trading_mode,
            symbols=strategy.symbols,
            timeframe=strategy.timeframe,
            is_active=strategy.is_active,
        )

    except Exception as e:
        logger.error("strategy_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create strategy",
        )


@router.get("/", response_model=List[StrategyResponse])
async def list_strategies(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all strategies for the current user."""
    try:
        result = await db.execute(
            select(StrategyInstance).where(StrategyInstance.user_id == current_user.id)
        )
        strategies = result.scalars().all()

        return [
            StrategyResponse(
                id=str(s.id),
                name=s.name,
                description=s.description,
                status=s.status,
                trading_mode=s.trading_mode,
                symbols=s.symbols,
                timeframe=s.timeframe,
                is_active=s.is_active,
            )
            for s in strategies
        ]

    except Exception as e:
        logger.error("strategy_listing_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list strategies",
        )


@router.post("/{strategy_id}/start")
async def start_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a strategy."""
    try:
        # Verify strategy belongs to user
        result = await db.execute(
            select(StrategyInstance).where(
                StrategyInstance.id == strategy_id,
                StrategyInstance.user_id == current_user.id,
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Start strategy
        success = await strategy_executor.start_strategy(strategy_id, db)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start strategy",
            )

        return {"message": "Strategy started successfully", "strategy_id": str(strategy_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("strategy_start_failed", strategy_id=str(strategy_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start strategy",
        )


@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop a strategy."""
    try:
        # Verify strategy belongs to user
        result = await db.execute(
            select(StrategyInstance).where(
                StrategyInstance.id == strategy_id,
                StrategyInstance.user_id == current_user.id,
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Stop strategy
        success = await strategy_executor.stop_strategy(strategy_id, db)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop strategy",
            )

        return {"message": "Strategy stopped successfully", "strategy_id": str(strategy_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("strategy_stop_failed", strategy_id=str(strategy_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop strategy",
        )
