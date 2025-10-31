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
from ...models.trading import TradeOrder, Position, OrderStatus, PositionStatus
from ...core.security import get_current_active_user
from ...services.strategy_engine.executor import strategy_executor


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
