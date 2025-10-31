/**
 * Strategy card component displaying strategy instance information.
 */
'use client';

import React from 'react';
import type { StrategyInstance, PerformanceMetrics } from '../../types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { PlayCircle, StopCircle, TrendingUp, TrendingDown } from 'lucide-react';

interface StrategyCardProps {
  strategy: StrategyInstance;
  metrics?: PerformanceMetrics;
  onStart?: () => void;
  onStop?: () => void;
  onViewDetails?: () => void;
}

export function StrategyCard({ strategy, metrics, onStart, onStop, onViewDetails }: StrategyCardProps) {
  const isRunning = strategy.status === 'running';
  const isProfitable = (metrics?.net_pnl || 0) >= 0;

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'stopped':
        return 'secondary';
      case 'paused':
        return 'warning';
      case 'error':
        return 'destructive';
      default:
        return 'default';
    }
  };

  const getTradingModeColor = (mode: string) => {
    return mode === 'live' ? 'destructive' : 'secondary';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-xl">{strategy.name}</CardTitle>
            <CardDescription className="mt-1">
              {strategy.symbol} • {strategy.timeframe}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge variant={getStatusColor(strategy.status)}>
              {strategy.status.toUpperCase()}
            </Badge>
            <Badge variant={getTradingModeColor(strategy.trading_mode)}>
              {strategy.trading_mode.toUpperCase()}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Performance Metrics */}
          {metrics && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">Total P&L</p>
                <p className={`text-2xl font-bold ${isProfitable ? 'text-green-600' : 'text-red-600'}`}>
                  {isProfitable ? <TrendingUp className="inline w-5 h-5 mr-1" /> : <TrendingDown className="inline w-5 h-5 mr-1" />}
                  {formatCurrency(metrics.net_pnl)}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">ROI</p>
                <p className={`text-2xl font-bold ${isProfitable ? 'text-green-600' : 'text-red-600'}`}>
                  {formatPercentage(metrics.roi_percentage)}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">Win Rate</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {metrics.win_rate.toFixed(2)}%
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Trades</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {metrics.total_trades}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">Sharpe Ratio</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {metrics.sharpe_ratio.toFixed(2)}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">Max Drawdown</p>
                <p className="text-lg font-semibold text-red-600">
                  {formatPercentage(-metrics.max_drawdown_percentage)}
                </p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            {isRunning ? (
              <Button variant="destructive" size="sm" onClick={onStop} className="flex-1">
                <StopCircle className="w-4 h-4 mr-2" />
                Stop
              </Button>
            ) : (
              <Button variant="default" size="sm" onClick={onStart} className="flex-1">
                <PlayCircle className="w-4 h-4 mr-2" />
                Start
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={onViewDetails} className="flex-1">
              View Details
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
