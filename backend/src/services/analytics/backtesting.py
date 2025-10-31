"""
Backtesting engine for strategy validation.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.strategy import Strategy, BacktestResult
from ...models.market_data import Candle, Tick
from ...services.strategy_engine.base import StrategyEngine, Signal
from ...services.strategy_engine.indicators import TechnicalIndicators
from ...utils.logging import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """Engine for backtesting trading strategies."""

    def __init__(self):
        """Initialize backtest engine."""
        self.indicators = TechnicalIndicators()

    async def run_backtest(
        self,
        strategy_engine: StrategyEngine,
        strategy_id: int,
        user_id: int,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
        db: AsyncSession,
        name: Optional[str] = None
    ) -> BacktestResult:
        """
        Run a backtest for a strategy.

        Args:
            strategy_engine: Strategy engine implementation
            strategy_id: Strategy ID
            user_id: User ID
            symbol: Trading symbol
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Initial capital
            db: Database session
            name: Optional backtest name

        Returns:
            BacktestResult with performance metrics
        """
        logger.info(f"Starting backtest for strategy {strategy_id} from {start_date} to {end_date}")

        # Load historical data
        candles = await self._load_historical_data(symbol, start_date, end_date, db)

        if not candles:
            raise ValueError(f"No historical data found for {symbol} between {start_date} and {end_date}")

        logger.info(f"Loaded {len(candles)} candles for backtesting")

        # Run backtest simulation
        trades, equity_curve = await self._simulate_trading(
            strategy_engine,
            symbol,
            candles,
            initial_capital
        )

        # Calculate performance metrics
        metrics = self._calculate_metrics(
            trades,
            equity_curve,
            initial_capital,
            start_date,
            end_date
        )

        # Create backtest result
        backtest_result = BacktestResult(
            strategy_id=strategy_id,
            user_id=user_id,
            name=name or f"Backtest {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            start_date=start_date,
            end_date=end_date,
            symbols=[symbol],
            initial_capital=initial_capital,
            total_return=metrics['total_return'],
            total_return_percentage=metrics['total_return_percentage'],
            annualized_return=metrics['annualized_return'],
            max_drawdown=metrics['max_drawdown'],
            max_drawdown_percentage=metrics['max_drawdown_percentage'],
            total_trades=metrics['total_trades'],
            winning_trades=metrics['winning_trades'],
            losing_trades=metrics['losing_trades'],
            win_rate=metrics['win_rate'],
            sharpe_ratio=metrics['sharpe_ratio'],
            sortino_ratio=metrics['sortino_ratio'],
            calmar_ratio=metrics['calmar_ratio'],
            metrics=metrics,
            trades=trades
        )

        db.add(backtest_result)
        await db.commit()
        await db.refresh(backtest_result)

        logger.info(f"Backtest completed: {metrics['total_trades']} trades, {metrics['win_rate']:.2f}% win rate")

        return backtest_result

    async def _load_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession,
        timeframe: str = "1h"
    ) -> List[Candle]:
        """
        Load historical candle data for backtesting.

        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            db: Database session
            timeframe: Candle timeframe

        Returns:
            List of candles
        """
        # Query candles from database
        result = await db.execute(
            select(Candle)
            .where(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe,
                Candle.timestamp >= start_date,
                Candle.timestamp <= end_date
            )
            .order_by(Candle.timestamp.asc())
        )
        candles = list(result.scalars().all())

        # If no data in database, generate simulated data for demo
        if not candles:
            logger.warning(f"No historical data found in database, generating simulated data")
            candles = self._generate_simulated_data(symbol, start_date, end_date, timeframe)

        return candles

    def _generate_simulated_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1h"
    ) -> List[Candle]:
        """
        Generate simulated candle data for backtesting (for demo purposes).

        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            timeframe: Candle timeframe

        Returns:
            List of simulated candles
        """
        candles = []
        current_time = start_date
        base_price = 100.0
        trend = 0.0001  # Slight upward trend

        while current_time <= end_date:
            # Simple random walk with trend
            change = np.random.normal(trend, 0.02)
            base_price = base_price * (1 + change)

            # Generate OHLC
            open_price = base_price
            high_price = base_price * (1 + abs(np.random.normal(0, 0.01)))
            low_price = base_price * (1 - abs(np.random.normal(0, 0.01)))
            close_price = base_price * (1 + np.random.normal(0, 0.005))

            volume = int(np.random.uniform(1000, 10000))

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=current_time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            )
            candles.append(candle)

            # Move to next timeframe
            current_time += timedelta(hours=1)

        return candles

    async def _simulate_trading(
        self,
        strategy_engine: StrategyEngine,
        symbol: str,
        candles: List[Candle],
        initial_capital: float
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Simulate trading using strategy engine on historical data.

        Args:
            strategy_engine: Strategy engine
            symbol: Trading symbol
            candles: Historical candles
            initial_capital: Initial capital

        Returns:
            Tuple of (trades list, equity curve)
        """
        cash = initial_capital
        position = None
        trades = []
        equity_curve = []

        for i, candle in enumerate(candles):
            # Calculate indicators using historical data up to this point
            historical_candles = candles[max(0, i-50):i+1]  # Use last 50 candles for indicators

            if len(historical_candles) < 20:  # Need minimum data for indicators
                equity_curve.append({
                    'timestamp': candle.timestamp.isoformat(),
                    'equity': cash,
                    'cash': cash,
                    'position_value': 0
                })
                continue

            # Calculate indicators
            try:
                indicators = await strategy_engine.calculate_indicators(symbol, historical_candles)
            except Exception as e:
                logger.warning(f"Error calculating indicators: {e}")
                indicators = {}

            # Create a simulated tick from candle
            tick = Tick(
                symbol=symbol,
                price=candle.close,
                volume=candle.volume,
                timestamp=candle.timestamp
            )

            # Get signal from strategy (would need to be modified to work without DB)
            # For simplicity, we'll use a basic strategy signal
            signal = self._generate_signal(symbol, candle, indicators, position)

            # Execute signal
            if signal:
                if signal.signal_type == 'entry' and position is None:
                    # Open position
                    quantity = int(cash * 0.95 / candle.close)  # Use 95% of cash
                    if quantity > 0:
                        cost = quantity * candle.close
                        cash -= cost

                        position = {
                            'entry_price': candle.close,
                            'quantity': quantity,
                            'entry_time': candle.timestamp,
                            'side': signal.side.value
                        }

                        logger.debug(f"Opened {signal.side.value} position: {quantity} @ {candle.close}")

                elif signal.signal_type == 'exit' and position is not None:
                    # Close position
                    exit_value = position['quantity'] * candle.close
                    cash += exit_value

                    # Calculate P&L
                    if position['side'] == 'buy':
                        pnl = (candle.close - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - candle.close) * position['quantity']

                    trade = {
                        'entry_time': position['entry_time'].isoformat(),
                        'exit_time': candle.timestamp.isoformat(),
                        'entry_price': position['entry_price'],
                        'exit_price': candle.close,
                        'quantity': position['quantity'],
                        'side': position['side'],
                        'pnl': pnl,
                        'return_percentage': (pnl / (position['entry_price'] * position['quantity'])) * 100
                    }
                    trades.append(trade)

                    logger.debug(f"Closed position: P&L {pnl:.2f}")
                    position = None

            # Calculate equity
            position_value = 0
            if position:
                position_value = position['quantity'] * candle.close

            equity = cash + position_value

            equity_curve.append({
                'timestamp': candle.timestamp.isoformat(),
                'equity': equity,
                'cash': cash,
                'position_value': position_value
            })

        # Close any open position at the end
        if position:
            exit_value = position['quantity'] * candles[-1].close
            cash += exit_value

            if position['side'] == 'buy':
                pnl = (candles[-1].close - position['entry_price']) * position['quantity']
            else:
                pnl = (position['entry_price'] - candles[-1].close) * position['quantity']

            trade = {
                'entry_time': position['entry_time'].isoformat(),
                'exit_time': candles[-1].timestamp.isoformat(),
                'entry_price': position['entry_price'],
                'exit_price': candles[-1].close,
                'quantity': position['quantity'],
                'side': position['side'],
                'pnl': pnl,
                'return_percentage': (pnl / (position['entry_price'] * position['quantity'])) * 100
            }
            trades.append(trade)

        return trades, equity_curve

    def _generate_signal(
        self,
        symbol: str,
        candle: Candle,
        indicators: Dict,
        current_position: Optional[Dict]
    ) -> Optional[Signal]:
        """
        Generate a simple signal based on indicators (for demonstration).

        In production, this would call the actual strategy engine's signal generation.

        Args:
            symbol: Trading symbol
            candle: Current candle
            indicators: Calculated indicators
            current_position: Current position if any

        Returns:
            Signal or None
        """
        # Simple moving average crossover strategy for demo
        if 'sma_20' in indicators and 'sma_50' in indicators:
            sma_20 = indicators['sma_20']
            sma_50 = indicators['sma_50']

            # Buy signal: SMA20 crosses above SMA50
            if sma_20 > sma_50 and current_position is None:
                from ...models.trading import OrderSide
                return Signal(
                    signal_type='entry',
                    symbol=symbol,
                    side=OrderSide.BUY,
                    price=candle.close,
                    strength=1.0,
                    reason="SMA20 crossed above SMA50"
                )

            # Sell signal: SMA20 crosses below SMA50
            if sma_20 < sma_50 and current_position is not None:
                from ...models.trading import OrderSide
                return Signal(
                    signal_type='exit',
                    symbol=symbol,
                    side=OrderSide.SELL,
                    price=candle.close,
                    strength=1.0,
                    reason="SMA20 crossed below SMA50"
                )

        return None

    def _calculate_metrics(
        self,
        trades: List[Dict],
        equity_curve: List[Dict],
        initial_capital: float,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Calculate performance metrics from backtest results.

        Args:
            trades: List of trades
            equity_curve: Equity curve data
            initial_capital: Initial capital
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            Dictionary of performance metrics
        """
        if not trades:
            return {
                'total_return': 0.0,
                'total_return_percentage': 0.0,
                'annualized_return': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_percentage': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': None,
                'sortino_ratio': None,
                'calmar_ratio': None,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0
            }

        # Calculate basic statistics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]

        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0

        # Calculate returns
        final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
        total_return = final_equity - initial_capital
        total_return_percentage = (total_return / initial_capital * 100) if initial_capital > 0 else 0

        # Annualized return
        days = (end_date - start_date).days
        years = days / 365.0 if days > 0 else 1
        annualized_return = ((final_equity / initial_capital) ** (1 / years) - 1) * 100 if years > 0 and initial_capital > 0 else 0

        # Max drawdown
        peak = initial_capital
        max_drawdown = 0
        for point in equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            drawdown = peak - point['equity']
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_percentage = (max_drawdown / peak * 100) if peak > 0 else 0

        # Sharpe and Sortino ratios
        returns = [t['return_percentage'] for t in trades]
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else None

            # Sortino uses only downside deviation
            negative_returns = [r for r in returns if r < 0]
            if negative_returns:
                downside_std = np.std(negative_returns)
                sortino_ratio = (mean_return / downside_std) * np.sqrt(252) if downside_std > 0 else None
            else:
                sortino_ratio = None
        else:
            sharpe_ratio = None
            sortino_ratio = None

        # Calmar ratio
        calmar_ratio = (annualized_return / max_drawdown_percentage) if max_drawdown_percentage > 0 else None

        return {
            'total_return': total_return,
            'total_return_percentage': total_return_percentage,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'max_drawdown_percentage': max_drawdown_percentage,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'average_win': total_profit / len(winning_trades) if winning_trades else 0,
            'average_loss': total_loss / len(losing_trades) if losing_trades else 0,
            'largest_win': max((t['pnl'] for t in winning_trades), default=0),
            'largest_loss': min((t['pnl'] for t in losing_trades), default=0),
            'total_profit': total_profit,
            'total_loss': total_loss
        }


# Global backtest engine instance
backtest_engine = BacktestEngine()
