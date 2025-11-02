"""Trading API endpoints."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_current_active_user
from src.models.database import get_db
from src.models.trading import Position, PositionStatus, TradeOrder
from src.models.user import User
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class PositionResponse(BaseModel):
    """Position response."""

    id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    status: str

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Order response."""

    id: str
    symbol: str
    order_type: str
    side: str
    quantity: float
    price: float | None
    filled_quantity: float
    status: str

    class Config:
        from_attributes = True


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    strategy_id: UUID | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get open positions."""
    try:
        query = select(Position).join(Position.strategy).where(
            Position.strategy.has(user_id=current_user.id),
            Position.status == PositionStatus.OPEN,
        )

        if strategy_id:
            query = query.where(Position.strategy_id == strategy_id)

        result = await db.execute(query)
        positions = result.scalars().all()

        return [
            PositionResponse(
                id=str(p.id),
                symbol=p.symbol,
                side=p.side.value,
                quantity=p.quantity,
                entry_price=p.entry_price,
                current_price=p.current_price,
                unrealized_pnl=p.unrealized_pnl,
                realized_pnl=p.realized_pnl,
                status=p.status.value,
            )
            for p in positions
        ]

    except Exception as e:
        logger.error("get_positions_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get positions")


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    strategy_id: UUID | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trade orders."""
    try:
        query = select(TradeOrder).join(TradeOrder.strategy).where(
            TradeOrder.strategy.has(user_id=current_user.id)
        )

        if strategy_id:
            query = query.where(TradeOrder.strategy_id == strategy_id)

        query = query.order_by(TradeOrder.created_at.desc()).limit(100)

        result = await db.execute(query)
        orders = result.scalars().all()

        return [
            OrderResponse(
                id=str(o.id),
                symbol=o.symbol,
                order_type=o.order_type.value,
                side=o.side.value,
                quantity=o.quantity,
                price=o.price,
                filled_quantity=o.filled_quantity,
                status=o.status.value,
            )
            for o in orders
        ]

    except Exception as e:
        logger.error("get_orders_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get orders")
