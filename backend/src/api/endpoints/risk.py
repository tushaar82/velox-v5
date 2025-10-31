"""
Risk management API endpoints.
Manages risk parameters and monitors risk metrics.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from ...models.database import get_db
from ...models.user import User, RiskParameters
from ...core.security import get_current_active_user
from ...services.strategy_engine.risk_manager import risk_manager


router = APIRouter()


# Pydantic schemas
class RiskParametersCreate(BaseModel):
    """Create/update risk parameters request."""
    max_daily_loss_percentage: float = Field(default=5.0, ge=0, le=100)
    max_daily_loss_amount: float | None = Field(default=None, ge=0)
    max_position_size_percentage: float = Field(default=10.0, ge=0, le=100)
    max_positions_per_strategy: int = Field(default=50, ge=1)
    max_drawdown_percentage: float = Field(default=15.0, ge=0, le=100)
    max_trades_per_day: int | None = Field(default=None, ge=1)
    max_loss_per_trade: float | None = Field(default=None, ge=0)


class RiskParametersResponse(BaseModel):
    """Risk parameters response."""
    id: int
    user_id: int
    max_daily_loss_percentage: float
    max_daily_loss_amount: float | None
    max_position_size_percentage: float
    max_positions_per_strategy: int
    max_drawdown_percentage: float
    max_trades_per_day: int | None
    max_loss_per_trade: float | None

    class Config:
        from_attributes = True


class RiskMetricsResponse(BaseModel):
    """Current risk metrics response."""
    daily_pnl: float
    drawdown_amount: float
    drawdown_percentage: float
    open_positions_count: int
    is_within_limits: bool
    violations: list[dict] = []


@router.get("/parameters", response_model=RiskParametersResponse)
async def get_risk_parameters(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's risk parameters."""
    result = await db.execute(
        select(RiskParameters)
        .where(RiskParameters.user_id == current_user.id)
    )
    params = result.scalar_one_or_none()

    if not params:
        # Return default values if not set
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk parameters not set. Please create them first."
        )

    return params


@router.post("/parameters", response_model=RiskParametersResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_parameters(
    params_data: RiskParametersCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update user's risk parameters."""
    # Check if parameters already exist
    result = await db.execute(
        select(RiskParameters)
        .where(RiskParameters.user_id == current_user.id)
    )
    existing_params = result.scalar_one_or_none()

    if existing_params:
        # Update existing parameters
        existing_params.max_daily_loss_percentage = params_data.max_daily_loss_percentage
        existing_params.max_daily_loss_amount = params_data.max_daily_loss_amount
        existing_params.max_position_size_percentage = params_data.max_position_size_percentage
        existing_params.max_positions_per_strategy = params_data.max_positions_per_strategy
        existing_params.max_drawdown_percentage = params_data.max_drawdown_percentage
        existing_params.max_trades_per_day = params_data.max_trades_per_day
        existing_params.max_loss_per_trade = params_data.max_loss_per_trade

        await db.commit()
        await db.refresh(existing_params)
        return existing_params
    else:
        # Create new parameters
        params = RiskParameters(
            user_id=current_user.id,
            max_daily_loss_percentage=params_data.max_daily_loss_percentage,
            max_daily_loss_amount=params_data.max_daily_loss_amount,
            max_position_size_percentage=params_data.max_position_size_percentage,
            max_positions_per_strategy=params_data.max_positions_per_strategy,
            max_drawdown_percentage=params_data.max_drawdown_percentage,
            max_trades_per_day=params_data.max_trades_per_day,
            max_loss_per_trade=params_data.max_loss_per_trade
        )

        db.add(params)
        await db.commit()
        await db.refresh(params)
        return params


@router.get("/metrics/{strategy_instance_id}", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    strategy_instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current risk metrics for a strategy instance."""
    # Verify strategy belongs to user
    from ...models.strategy import StrategyInstance
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy instance not found"
        )

    # Calculate metrics
    daily_pnl = await risk_manager.calculate_daily_pnl(strategy_instance_id, db)

    # Calculate current equity
    current_equity = instance.max_position_size + instance.total_pnl
    drawdown_amount, drawdown_percentage = await risk_manager.calculate_drawdown(
        strategy_instance_id,
        current_equity,
        db
    )

    # Check risk limits
    is_within_limits, violation = await risk_manager.check_risk_limits(
        strategy_instance_id,
        current_user.id,
        db
    )

    # Get open positions count
    from ...models.trading import Position, PositionStatus
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(Position.id))
        .where(
            Position.strategy_instance_id == strategy_instance_id,
            Position.status == PositionStatus.OPEN
        )
    )
    open_positions = result.scalar_one()

    violations = []
    if not is_within_limits and violation:
        violations.append({
            "type": violation.violation_type,
            "current_value": violation.current_value,
            "limit_value": violation.limit_value,
            "severity": violation.severity,
            "message": violation.message
        })

    return RiskMetricsResponse(
        daily_pnl=daily_pnl,
        drawdown_amount=drawdown_amount,
        drawdown_percentage=drawdown_percentage,
        open_positions_count=open_positions,
        is_within_limits=is_within_limits,
        violations=violations
    )


@router.post("/close-all-positions/{strategy_instance_id}")
async def close_all_positions(
    strategy_instance_id: int,
    reason: str = "Manual closure",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually close all positions for a strategy."""
    # Verify strategy belongs to user
    from ...models.strategy import StrategyInstance
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy instance not found"
        )

    # Close all positions
    closed_count = await risk_manager.close_all_positions(
        strategy_instance_id,
        reason,
        db
    )

    return {
        "message": f"Closed {closed_count} positions",
        "strategy_instance_id": strategy_instance_id,
        "closed_count": closed_count
    }
