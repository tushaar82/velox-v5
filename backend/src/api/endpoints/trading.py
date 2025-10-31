"""
Trading API endpoints.
Handles orders, positions, and trading operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from ...models.database import get_db
from ...models.user import User
from ...models.trading import TradeOrder, Position, OrderStatus, PositionStatus, TrailingStoploss
from ...core.security import get_current_active_user
from ...services.strategy_engine.executor import strategy_executor
from ...services.strategy_engine.trailing_stoploss import trailing_stoploss_service


router = APIRouter()


# Pydantic schemas
class OrderCreate(BaseModel):
    """Create order request."""
    strategy_instance_id: int
    symbol: str
    side: str
    quantity: int
    order_type: str = "market"
    price: float | None = None


class OrderResponse(BaseModel):
    """Order response."""
    id: int
    symbol: str
    side: str
    quantity: int
    status: str
    price: float | None
    filled_price: float | None
    created_at: str

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """Position response."""
    id: int
    symbol: str
    side: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    status: str

    class Config:
        from_attributes = True


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    strategy_instance_id: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's orders."""
    query = select(TradeOrder).where(TradeOrder.user_id == current_user.id)

    if strategy_instance_id:
        query = query.where(TradeOrder.strategy_instance_id == strategy_instance_id)

    result = await db.execute(query.order_by(TradeOrder.created_at.desc()).limit(100))
    orders = result.scalars().all()

    return [
        OrderResponse(
            id=order.id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            status=order.status.value,
            price=order.price,
            filled_price=order.filled_price,
            created_at=order.created_at.isoformat()
        )
        for order in orders
    ]


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific order."""
    result = await db.execute(
        select(TradeOrder).where(
            TradeOrder.id == order_id,
            TradeOrder.user_id == current_user.id
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return OrderResponse(
        id=order.id,
        symbol=order.symbol,
        side=order.side.value,
        quantity=order.quantity,
        status=order.status.value,
        price=order.price,
        filled_price=order.filled_price,
        created_at=order.created_at.isoformat()
    )


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    strategy_instance_id: int | None = None,
    status_filter: str = "open",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's positions."""
    query = select(Position).where(Position.user_id == current_user.id)

    if strategy_instance_id:
        query = query.where(Position.strategy_instance_id == strategy_instance_id)

    if status_filter == "open":
        query = query.where(Position.status == PositionStatus.OPEN)
    elif status_filter == "closed":
        query = query.where(Position.status == PositionStatus.CLOSED)

    result = await db.execute(query.order_by(Position.created_at.desc()).limit(100))
    positions = result.scalars().all()

    return [
        PositionResponse(
            id=pos.id,
            symbol=pos.symbol,
            side=pos.side.value,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            current_price=pos.current_price,
            unrealized_pnl=pos.unrealized_pnl,
            status=pos.status.value
        )
        for pos in positions
    ]


@router.get("/positions/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific position."""
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )

    return PositionResponse(
        id=position.id,
        symbol=position.symbol,
        side=position.side.value,
        quantity=position.quantity,
        entry_price=position.entry_price,
        current_price=position.current_price,
        unrealized_pnl=position.unrealized_pnl,
        status=position.status.value
    )


# Trailing Stoploss Endpoints

class TrailingStoplossCreate(BaseModel):
    """Create trailing stoploss request."""
    trailing_percentage: float
    trailing_amount: float | None = None


class TrailingStoplossResponse(BaseModel):
    """Trailing stoploss response."""
    id: int
    position_id: int
    trailing_percentage: float
    trailing_amount: float | None
    highest_price: float
    current_stop_price: float
    is_active: bool
    is_triggered: bool

    class Config:
        from_attributes = True


@router.post("/positions/{position_id}/trailing-stoploss", response_model=TrailingStoplossResponse)
async def create_trailing_stoploss(
    position_id: int,
    stoploss_data: TrailingStoplossCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create trailing stoploss for a position."""
    # Verify position belongs to user
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id,
            Position.status == PositionStatus.OPEN
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found or already closed"
        )

    # Check if trailing stoploss already exists
    result = await db.execute(
        select(TrailingStoploss).where(
            TrailingStoploss.position_id == position_id,
            TrailingStoploss.is_active == True
        )
    )
    existing_stoploss = result.scalar_one_or_none()

    if existing_stoploss:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trailing stoploss already exists for this position"
        )

    # Create trailing stoploss
    stoploss = await trailing_stoploss_service.create_trailing_stoploss(
        position,
        stoploss_data.trailing_percentage,
        stoploss_data.trailing_amount,
        db
    )

    return stoploss


@router.get("/positions/{position_id}/trailing-stoploss", response_model=TrailingStoplossResponse)
async def get_trailing_stoploss(
    position_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get trailing stoploss for a position."""
    # Verify position belongs to user
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )

    # Get trailing stoploss
    result = await db.execute(
        select(TrailingStoploss).where(
            TrailingStoploss.position_id == position_id
        )
    )
    stoploss = result.scalar_one_or_none()

    if not stoploss:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trailing stoploss not found"
        )

    return stoploss


@router.delete("/positions/{position_id}/trailing-stoploss")
async def delete_trailing_stoploss(
    position_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate trailing stoploss for a position."""
    # Verify position belongs to user
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )

    # Deactivate trailing stoploss
    success = await trailing_stoploss_service.deactivate_trailing_stoploss(
        position_id,
        db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trailing stoploss not found"
        )

    return {"message": "Trailing stoploss deactivated", "position_id": position_id}
