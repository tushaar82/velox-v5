"""
Market data API endpoints.
Provides access to ticks, candles, and market information.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel

from ...models.database import get_timescale_db
from ...models.market_data import Tick, Candle, CandleInterval
from ...core.security import get_current_active_user
from ...models.user import User


router = APIRouter()


# Pydantic schemas
class TickResponse(BaseModel):
    """Tick data response."""
    time: str
    symbol: str
    price: float
    volume: int
    bid: float | None
    ask: float | None

    class Config:
        from_attributes = True


class CandleResponse(BaseModel):
    """Candle data response."""
    time: str
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    class Config:
        from_attributes = True


@router.get("/ticks/{symbol}", response_model=List[TickResponse])
async def get_ticks(
    symbol: str,
    limit: int = Query(default=100, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_timescale_db)
):
    """Get recent tick data for symbol."""
    result = await db.execute(
        select(Tick)
        .where(Tick.symbol == symbol.upper())
        .order_by(desc(Tick.time))
        .limit(limit)
    )
    ticks = result.scalars().all()

    return [
        TickResponse(
            time=tick.time.isoformat(),
            symbol=tick.symbol,
            price=tick.price,
            volume=tick.volume,
            bid=tick.bid,
            ask=tick.ask
        )
        for tick in reversed(ticks)
    ]


@router.get("/candles/{symbol}", response_model=List[CandleResponse])
async def get_candles(
    symbol: str,
    interval: CandleInterval = Query(default=CandleInterval.ONE_MINUTE),
    limit: int = Query(default=100, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_timescale_db)
):
    """Get candle data for symbol."""
    result = await db.execute(
        select(Candle)
        .where(
            Candle.symbol == symbol.upper(),
            Candle.interval == interval
        )
        .order_by(desc(Candle.time))
        .limit(limit)
    )
    candles = result.scalars().all()

    return [
        CandleResponse(
            time=candle.time.isoformat(),
            symbol=candle.symbol,
            interval=candle.interval.value,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume
        )
        for candle in reversed(candles)
    ]


@router.get("/latest-price/{symbol}")
async def get_latest_price(
    symbol: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_timescale_db)
):
    """Get latest price for symbol."""
    result = await db.execute(
        select(Tick)
        .where(Tick.symbol == symbol.upper())
        .order_by(desc(Tick.time))
        .limit(1)
    )
    tick = result.scalar_one_or_none()

    if not tick:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for symbol {symbol}"
        )

    return {
        "symbol": tick.symbol,
        "price": tick.price,
        "bid": tick.bid,
        "ask": tick.ask,
        "time": tick.time.isoformat()
    }
