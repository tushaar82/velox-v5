"""Technical indicators calculator."""
import numpy as np
import pandas as pd
from typing import List, Tuple

from src.utils.logging import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Technical indicators calculator."""

    @staticmethod
    def sma(prices: List[float], period: int) -> float:
        """
        Calculate Simple Moving Average.

        Args:
            prices: List of prices
            period: Period for SMA

        Returns:
            SMA value
        """
        if len(prices) < period:
            return 0.0
        return sum(prices[-period:]) / period

    @staticmethod
    def ema(prices: List[float], period: int) -> float:
        """
        Calculate Exponential Moving Average.

        Args:
            prices: List of prices
            period: Period for EMA

        Returns:
            EMA value
        """
        if len(prices) < period:
            return 0.0

        prices_array = np.array(prices)
        ema = pd.Series(prices_array).ewm(span=period, adjust=False).mean().iloc[-1]
        return float(ema)

    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """
        Calculate Relative Strength Index.

        Args:
            prices: List of prices
            period: Period for RSI

        Returns:
            RSI value (0-100)
        """
        if len(prices) < period + 1:
            return 50.0

        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
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
    def macd(
        prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ) -> Tuple[float, float, float]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            prices: List of prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        if len(prices) < slow_period:
            return 0.0, 0.0, 0.0

        prices_series = pd.Series(prices)
        fast_ema = prices_series.ewm(span=fast_period, adjust=False).mean()
        slow_ema = prices_series.ewm(span=slow_period, adjust=False).mean()

        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return (
            float(macd_line.iloc[-1]),
            float(signal_line.iloc[-1]),
            float(histogram.iloc[-1]),
        )

    @staticmethod
    def bollinger_bands(
        prices: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: List of prices
            period: Period for moving average
            std_dev: Number of standard deviations

        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        if len(prices) < period:
            return 0.0, 0.0, 0.0

        prices_array = np.array(prices[-period:])
        middle = np.mean(prices_array)
        std = np.std(prices_array)

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return float(upper), float(middle), float(lower)

    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """
        Calculate Average True Range.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: Period for ATR

        Returns:
            ATR value
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(high_low, high_close, low_close))

        if len(true_ranges) < period:
            return 0.0

        atr = np.mean(true_ranges[-period:])
        return float(atr)

    @staticmethod
    def stochastic(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Tuple[float, float]:
        """
        Calculate Stochastic Oscillator.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: Period for stochastic

        Returns:
            Tuple of (%K, %D)
        """
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return 50.0, 50.0

        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        current_close = closes[-1]

        if highest_high == lowest_low:
            k = 50.0
        else:
            k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100

        # Simple %D (3-period SMA of %K)
        # For simplicity, returning %K as both values
        d = k

        return float(k), float(d)

    @staticmethod
    def adx(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> float:
        """
        Calculate Average Directional Index.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: Period for ADX

        Returns:
            ADX value
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            return 0.0

        # Simplified ADX calculation
        # In production, use ta-lib or more sophisticated calculation
        atr_val = TechnicalIndicators.atr(highs, lows, closes, period)
        if atr_val == 0:
            return 0.0

        return 25.0  # Placeholder

    @staticmethod
    def vwap(prices: List[float], volumes: List[float]) -> float:
        """
        Calculate Volume Weighted Average Price.

        Args:
            prices: List of prices
            volumes: List of volumes

        Returns:
            VWAP value
        """
        if len(prices) != len(volumes) or len(prices) == 0:
            return 0.0

        total_pv = sum(p * v for p, v in zip(prices, volumes))
        total_v = sum(volumes)

        if total_v == 0:
            return 0.0

        return total_pv / total_v
