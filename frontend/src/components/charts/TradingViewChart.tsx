/**
 * TradingView-style chart component using lightweight-charts.
 */
'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData } from 'lightweight-charts';
import type { Candle } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

interface TradingViewChartProps {
  data: Candle[];
  title?: string;
  height?: number;
}

export function TradingViewChart({ data, title = 'Price Chart', height = 500 }: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#d1d5db',
      },
      timeScale: {
        borderColor: '#d1d5db',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    seriesRef.current = candlestickSeries;

    // Handle window resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [height]);

  useEffect(() => {
    if (!seriesRef.current || !data || data.length === 0) return;

    // Convert Candle data to lightweight-charts format
    const chartData: CandlestickData[] = data.map((candle) => ({
      time: new Date(candle.timestamp).getTime() / 1000, // Convert to seconds
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    // Sort by time
    chartData.sort((a, b) => (a.time as number) - (b.time as number));

    seriesRef.current.setData(chartData);

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [data]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={chartContainerRef} style={{ position: 'relative' }} />
      </CardContent>
    </Card>
  );
}
