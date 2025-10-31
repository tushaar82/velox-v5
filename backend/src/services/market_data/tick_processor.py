"""
Real-time tick data processor.
Processes incoming market ticks and updates strategy engines.
"""
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.market_data import Tick
from ...models.strategy import StrategyInstance, StrategyStatus
from ...utils.logging import get_logger, log_performance
from ...utils.monitoring import tick_processing_histogram, PerformanceTracker


logger = get_logger(__name__)


class TickProcessor:
    """Processes real-time market tick data."""

    def __init__(self):
        """Initialize tick processor."""
        self.active_strategies: Dict[int, any] = {}
        self.latest_ticks: Dict[str, Tick] = {}

    @log_performance("tick_processing_latency")
    async def process_tick(
        self,
        tick_data: dict,
        db: AsyncSession
    ) -> None:
        """
        Process incoming tick data.

        Args:
            tick_data: Tick data dictionary
            db: Database session
        """
        with PerformanceTracker(tick_processing_histogram):
            try:
                # Parse tick data
                symbol = tick_data.get('symbol')
                price = tick_data.get('price')
                volume = tick_data.get('volume', 0)
                timestamp = tick_data.get('timestamp')

                if not symbol or not price:
                    logger.warning("Invalid tick data received", data=tick_data)
                    return

                # Create tick object
                tick = Tick(
                    time=datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow(),
                    symbol=symbol,
                    price=float(price),
                    bid=tick_data.get('bid'),
                    ask=tick_data.get('ask'),
                    volume=int(volume),
                    bid_volume=tick_data.get('bid_volume'),
                    ask_volume=tick_data.get('ask_volume'),
                    exchange=tick_data.get('exchange')
                )

                # Store latest tick
                self.latest_ticks[symbol] = tick

                # Process tick for all active strategies trading this symbol
                await self._process_for_strategies(tick, db)

                logger.debug(
                    f"Tick processed for {symbol}",
                    symbol=symbol,
                    price=price,
                    volume=volume
                )

            except Exception as e:
                logger.error(f"Error processing tick: {e}", exc_info=True)

    async def _process_for_strategies(
        self,
        tick: Tick,
        db: AsyncSession
    ) -> None:
        """
        Process tick for all relevant strategies.

        Args:
            tick: Tick data
            db: Database session
        """
        # Get active strategies trading this symbol
        result = await db.execute(
            select(StrategyInstance)
            .where(StrategyInstance.status == StrategyStatus.ACTIVE)
        )
        active_instances = result.scalars().all()

        for instance in active_instances:
            # Check if this strategy trades the symbol
            if tick.symbol in instance.symbols:
                # Process tick for this strategy
                # Note: This would integrate with the strategy engine
                logger.debug(
                    f"Processing tick for strategy {instance.id}",
                    strategy_id=instance.id,
                    symbol=tick.symbol
                )

    def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        """
        Get latest tick for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Latest tick if available
        """
        return self.latest_ticks.get(symbol)

    async def process_batch(
        self,
        ticks: List[dict],
        db: AsyncSession
    ) -> None:
        """
        Process batch of ticks.

        Args:
            ticks: List of tick data dictionaries
            db: Database session
        """
        for tick_data in ticks:
            await self.process_tick(tick_data, db)


# Global tick processor instance
tick_processor = TickProcessor()
