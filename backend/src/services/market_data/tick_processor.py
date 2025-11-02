"""Tick data processor for real-time market data."""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import get_timescale_db
from src.models.market_data import Candle, Tick
from src.utils.logging import get_logger
from src.utils.monitoring import tick_processing_duration, track_time

logger = get_logger(__name__)


class TickProcessor:
    """Process real-time tick data and generate candles."""

    def __init__(self):
        self.tick_buffer: Dict[str, List[Tick]] = {}
        self.candle_builders: Dict[str, Dict[str, CandleBuilder]] = {}

    async def process_tick(self, tick_data: Dict, db: AsyncSession) -> Tick:
        """
        Process a single tick.

        Args:
            tick_data: Raw tick data dictionary
            db: Database session

        Returns:
            Processed Tick object
        """
        with track_time(tick_processing_duration, {"symbol": tick_data["symbol"]}):
            # Create tick object
            tick = Tick(
                symbol=tick_data["symbol"],
                timestamp=tick_data.get("timestamp", datetime.utcnow()),
                last_price=tick_data["last_price"],
                last_quantity=tick_data.get("last_quantity", 0),
                bid_price=tick_data.get("bid_price"),
                bid_quantity=tick_data.get("bid_quantity"),
                ask_price=tick_data.get("ask_price"),
                ask_quantity=tick_data.get("ask_quantity"),
                volume=tick_data.get("volume", 0),
                open_interest=tick_data.get("open_interest"),
            )

            # Store tick in database
            try:
                db.add(tick)
                await db.commit()
                await db.refresh(tick)
            except Exception as e:
                logger.error("tick_storage_failed", symbol=tick.symbol, error=str(e))
                await db.rollback()

            # Update candle builders
            await self._update_candles(tick, db)

            # Add to buffer for strategy processing
            if tick.symbol not in self.tick_buffer:
                self.tick_buffer[tick.symbol] = []
            self.tick_buffer[tick.symbol].append(tick)

            # Keep buffer size manageable
            if len(self.tick_buffer[tick.symbol]) > 1000:
                self.tick_buffer[tick.symbol] = self.tick_buffer[tick.symbol][-1000:]

            logger.debug("tick_processed", symbol=tick.symbol, price=tick.last_price)

            return tick

    async def _update_candles(self, tick: Tick, db: AsyncSession) -> None:
        """Update candles with new tick data."""
        symbol = tick.symbol
        timeframes = ["1m", "5m", "15m", "1h", "1d"]

        if symbol not in self.candle_builders:
            self.candle_builders[symbol] = {}

        for timeframe in timeframes:
            if timeframe not in self.candle_builders[symbol]:
                self.candle_builders[symbol][timeframe] = CandleBuilder(symbol, timeframe)

            builder = self.candle_builders[symbol][timeframe]
            candle = await builder.add_tick(tick, db)

            if candle:
                logger.info(
                    "candle_formed",
                    symbol=symbol,
                    timeframe=timeframe,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                )

    def get_recent_ticks(self, symbol: str, count: int = 100) -> List[Tick]:
        """Get recent ticks for a symbol."""
        if symbol not in self.tick_buffer:
            return []
        return self.tick_buffer[symbol][-count:]


class CandleBuilder:
    """Build OHLCV candles from tick data."""

    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.current_candle: Optional[Candle] = None
        self.trades_count = 0

    async def add_tick(self, tick: Tick, db: AsyncSession) -> Optional[Candle]:
        """
        Add a tick to the candle builder.

        Args:
            tick: Tick data
            db: Database session

        Returns:
            Completed candle if period ended, None otherwise
        """
        candle_time = self._get_candle_timestamp(tick.timestamp)

        # Start new candle if needed
        if self.current_candle is None or self.current_candle.timestamp != candle_time:
            # Save previous candle
            completed_candle = None
            if self.current_candle is not None:
                completed_candle = await self._save_candle(self.current_candle, db)

            # Start new candle
            self.current_candle = Candle(
                symbol=self.symbol,
                timeframe=self.timeframe,
                timestamp=candle_time,
                open=tick.last_price,
                high=tick.last_price,
                low=tick.last_price,
                close=tick.last_price,
                volume=tick.volume,
                trades=1,
            )
            self.trades_count = 1

            return completed_candle

        # Update current candle
        self.current_candle.high = max(self.current_candle.high, tick.last_price)
        self.current_candle.low = min(self.current_candle.low, tick.last_price)
        self.current_candle.close = tick.last_price
        self.current_candle.volume += tick.volume
        self.trades_count += 1
        self.current_candle.trades = self.trades_count

        return None

    def _get_candle_timestamp(self, tick_time: datetime) -> datetime:
        """Get the candle timestamp for a given tick time."""
        # Simplified - round down to candle period
        if self.timeframe == "1m":
            return tick_time.replace(second=0, microsecond=0)
        elif self.timeframe == "5m":
            minute = (tick_time.minute // 5) * 5
            return tick_time.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "15m":
            minute = (tick_time.minute // 15) * 15
            return tick_time.replace(minute=minute, second=0, microsecond=0)
        elif self.timeframe == "1h":
            return tick_time.replace(minute=0, second=0, microsecond=0)
        elif self.timeframe == "1d":
            return tick_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return tick_time

    async def _save_candle(self, candle: Candle, db: AsyncSession) -> Candle:
        """Save candle to database."""
        try:
            db.add(candle)
            await db.commit()
            await db.refresh(candle)
            return candle
        except Exception as e:
            logger.error(
                "candle_storage_failed",
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                error=str(e),
            )
            await db.rollback()
            return candle


# Global tick processor instance
tick_processor = TickProcessor()
