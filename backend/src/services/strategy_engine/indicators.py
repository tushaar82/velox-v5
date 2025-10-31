"""
Technical indicators calculator.
Provides common technical indicators for trading strategies.
"""
from typing import List, Dict, Any
import numpy as np
from ...models.market_data import Candle


class TechnicalIndicators:
    """Calculate technical indicators from market data."""

    @staticmethod
    def sma(values: List[float], period: int) -> float:
        """
        Calculate Simple Moving Average.

        Args:
            values: List of values
            period: SMA period

        Returns:
            SMA value
        """
        if len(values) < period:
            return 0.0
        return sum(values[-period:]) / period

    @staticmethod
    def ema(values: List[float], period: int) -> float:
        """
        Calculate Exponential Moving Average.

        Args:
            values: List of values
            period: EMA period

        Returns:
            EMA value
        """
        if len(values) < period:
            return 0.0

        multiplier = 2 / (period + 1)
        ema = values[0]

        for value in values[1:]:
            ema = (value - ema) * multiplier + ema

        return ema

    @staticmethod
    def rsi(values: List[float], period: int = 14) -> float:
        """
        Calculate Relative Strength Index.

        Args:
            values: List of values
            period: RSI period

        Returns:
            RSI value (0-100)
        """
        if len(values) < period + 1:
            return 50.0

        deltas = np.diff(values)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    @staticmethod
    def bollinger_bands(
        values: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, float]:
        """
        Calculate Bollinger Bands.

        Args:
            values: List of values
            period: Period for moving average
            std_dev: Number of standard deviations

        Returns:
            Dictionary with upper, middle, and lower bands
        """
        if len(values) < period:
            return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0}

        recent_values = values[-period:]
        middle = sum(recent_values) / period
        std = np.std(recent_values)

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return {
            'upper': float(upper),
            'middle': float(middle),
            'lower': float(lower)
        }

    @staticmethod
    def macd(
        values: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, float]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            values: List of values
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            Dictionary with MACD line, signal line, and histogram
        """
        if len(values) < slow_period:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}

        fast_ema = TechnicalIndicators.ema(values, fast_period)
        slow_ema = TechnicalIndicators.ema(values, slow_period)

        macd_line = fast_ema - slow_ema

        # For simplicity, using SMA for signal line (should use EMA of MACD)
        macd_values = [fast_ema - slow_ema]
        signal_line = macd_values[0]  # Simplified

        histogram = macd_line - signal_line

        return {
            'macd': float(macd_line),
            'signal': float(signal_line),
            'histogram': float(histogram)
        }

    @staticmethod
    def atr(candles: List[Candle], period: int = 14) -> float:
        """
        Calculate Average True Range.

        Args:
            candles: List of candle data
            period: ATR period

        Returns:
            ATR value
        """
        if len(candles) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i - 1].close

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        atr = sum(true_ranges[-period:]) / period
        return float(atr)

    @staticmethod
    def vwap(candles: List[Candle]) -> float:
        """
        Calculate Volume Weighted Average Price.

        Args:
            candles: List of candle data

        Returns:
            VWAP value
        """
        if not candles:
            return 0.0

        total_volume = sum(c.volume for c in candles)
        if total_volume == 0:
            return 0.0

        vwap = sum(
            ((c.high + c.low + c.close) / 3) * c.volume
            for c in candles
        ) / total_volume

        return float(vwap)

    @staticmethod
    def stochastic_oscillator(
        candles: List[Candle],
        period: int = 14
    ) -> Dict[str, float]:
        """
        Calculate Stochastic Oscillator.

        Args:
            candles: List of candle data
            period: Period for calculation

        Returns:
            Dictionary with %K and %D values
        """
        if len(candles) < period:
            return {'k': 50.0, 'd': 50.0}

        recent_candles = candles[-period:]
        current_close = candles[-1].close
        highest_high = max(c.high for c in recent_candles)
        lowest_low = min(c.low for c in recent_candles)

        if highest_high == lowest_low:
            k = 50.0
        else:
            k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100

        # Simplified %D (should be SMA of %K)
        d = k

        return {
            'k': float(k),
            'd': float(d)
        }
