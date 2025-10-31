"""
TimescaleDB writer for market data.
Efficiently stores tick and candle data in time-series database.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from ...models.market_data import Tick, Candle, IndicatorValue, CandleInterval
from ...models.database import get_timescale_db
from ...utils.logging import get_logger


logger = get_logger(__name__)


class TimescaleWriter:
    """Writes market data to TimescaleDB."""

    async def write_tick(
        self,
        tick: Tick,
        db: AsyncSession
    ) -> None:
        """
        Write single tick to TimescaleDB.

        Args:
            tick: Tick data
            db: TimescaleDB session
        """
        try:
            db.add(tick)
            await db.commit()
            logger.debug(f"Tick written to TimescaleDB", symbol=tick.symbol)
        except Exception as e:
            logger.error(f"Error writing tick: {e}", exc_info=True)
            await db.rollback()

    async def write_ticks_batch(
        self,
        ticks: List[Tick],
        db: AsyncSession
    ) -> None:
        """
        Write batch of ticks to TimescaleDB.

        Args:
            ticks: List of tick data
            db: TimescaleDB session
        """
        try:
            db.add_all(ticks)
            await db.commit()
            logger.debug(f"Batch of {len(ticks)} ticks written to TimescaleDB")
        except Exception as e:
            logger.error(f"Error writing tick batch: {e}", exc_info=True)
            await db.rollback()

    async def write_candle(
        self,
        candle: Candle,
        db: AsyncSession
    ) -> None:
        """
        Write single candle to TimescaleDB.

        Args:
            candle: Candle data
            db: TimescaleDB session
        """
        try:
            db.add(candle)
            await db.commit()
            logger.debug(
                f"Candle written to TimescaleDB",
                symbol=candle.symbol,
                interval=candle.interval
            )
        except Exception as e:
            logger.error(f"Error writing candle: {e}", exc_info=True)
            await db.rollback()

    async def write_candles_batch(
        self,
        candles: List[Candle],
        db: AsyncSession
    ) -> None:
        """
        Write batch of candles to TimescaleDB.

        Args:
            candles: List of candle data
            db: TimescaleDB session
        """
        try:
            db.add_all(candles)
            await db.commit()
            logger.debug(f"Batch of {len(candles)} candles written to TimescaleDB")
        except Exception as e:
            logger.error(f"Error writing candle batch: {e}", exc_info=True)
            await db.rollback()

    async def write_indicator(
        self,
        indicator: IndicatorValue,
        db: AsyncSession
    ) -> None:
        """
        Write indicator value to TimescaleDB.

        Args:
            indicator: Indicator value
            db: TimescaleDB session
        """
        try:
            db.add(indicator)
            await db.commit()
            logger.debug(
                f"Indicator written to TimescaleDB",
                symbol=indicator.symbol,
                indicator=indicator.indicator_name
            )
        except Exception as e:
            logger.error(f"Error writing indicator: {e}", exc_info=True)
            await db.rollback()

    async def write_indicators_batch(
        self,
        indicators: List[IndicatorValue],
        db: AsyncSession
    ) -> None:
        """
        Write batch of indicator values to TimescaleDB.

        Args:
            indicators: List of indicator values
            db: TimescaleDB session
        """
        try:
            db.add_all(indicators)
            await db.commit()
            logger.debug(f"Batch of {len(indicators)} indicators written to TimescaleDB")
        except Exception as e:
            logger.error(f"Error writing indicator batch: {e}", exc_info=True)
            await db.rollback()

    async def create_candle_from_ticks(
        self,
        symbol: str,
        ticks: List[Tick],
        interval: CandleInterval,
        start_time: datetime
    ) -> Optional[Candle]:
        """
        Create candle from tick data.

        Args:
            symbol: Trading symbol
            ticks: List of ticks
            interval: Candle interval
            start_time: Candle start time

        Returns:
            Candle object if ticks available
        """
        if not ticks:
            return None

        prices = [t.price for t in ticks]
        volumes = [t.volume for t in ticks]

        candle = Candle(
            time=start_time,
            symbol=symbol,
            interval=interval,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=sum(volumes),
            trades=len(ticks)
        )

        return candle


# Global TimescaleDB writer instance
timescale_writer = TimescaleWriter()
