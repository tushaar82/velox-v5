/**
 * Risk metrics component displaying current risk status.
 */
'use client';

import React from 'react';
import type { RiskMetrics as RiskMetricsType, RiskParameters } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { AlertTriangle, CheckCircle, XCircle, Shield } from 'lucide-react';

interface RiskMetricsProps {
  metrics: RiskMetricsType;
  parameters?: RiskParameters;
}

export function RiskMetrics({ metrics, parameters }: RiskMetricsProps) {
  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      case 'info':
        return <CheckCircle className="w-5 h-5 text-blue-600" />;
      default:
        return null;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'destructive';
      case 'warning':
        return 'warning';
      case 'info':
        return 'default';
      default:
        return 'secondary';
    }
  };

  const getDailyPnLPercentage = () => {
    if (!parameters?.max_daily_loss_amount) return 0;
    return (Math.abs(metrics.daily_pnl) / parameters.max_daily_loss_amount) * 100;
  };

  const getDrawdownPercentageUsage = () => {
    if (!parameters?.max_drawdown_percentage) return 0;
    return (metrics.drawdown_percentage / parameters.max_drawdown_percentage) * 100;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Risk Management
          </CardTitle>
          {metrics.is_within_limits ? (
            <Badge variant="success">
              <CheckCircle className="w-3 h-3 mr-1" />
              Within Limits
            </Badge>
          ) : (
            <Badge variant="destructive">
              <XCircle className="w-3 h-3 mr-1" />
              Limit Breach
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Daily P&L */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Daily P&L
              </span>
              <span className={`text-lg font-bold ${metrics.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(metrics.daily_pnl)}
              </span>
            </div>
            {parameters?.max_daily_loss_amount && (
              <div className="space-y-1">
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      getDailyPnLPercentage() > 80 ? 'bg-red-600' : 'bg-green-600'
                    }`}
                    style={{ width: `${Math.min(getDailyPnLPercentage(), 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Limit: {formatCurrency(parameters.max_daily_loss_amount)} (
                  {parameters.max_daily_loss_percentage}%)
                </p>
              </div>
            )}
          </div>

          {/* Drawdown */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Current Drawdown
              </span>
              <div className="text-right">
                <span className="text-lg font-bold text-red-600">
                  {formatPercentage(metrics.drawdown_percentage)}
                </span>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatCurrency(metrics.drawdown_amount)}
                </p>
              </div>
            </div>
            {parameters?.max_drawdown_percentage && (
              <div className="space-y-1">
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      getDrawdownPercentageUsage() > 80 ? 'bg-red-600' : 'bg-yellow-600'
                    }`}
                    style={{ width: `${Math.min(getDrawdownPercentageUsage(), 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Limit: {formatPercentage(parameters.max_drawdown_percentage)}
                </p>
              </div>
            )}
          </div>

          {/* Open Positions */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Open Positions
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {metrics.open_positions_count}
              </span>
            </div>
            {parameters?.max_positions_per_strategy && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Limit: {parameters.max_positions_per_strategy} positions
              </p>
            )}
          </div>

          {/* Risk Violations */}
          {metrics.violations.length > 0 && (
            <div className="space-y-3 pt-2 border-t border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-600" />
                Risk Alerts
              </h4>
              {metrics.violations.map((violation, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                >
                  {getSeverityIcon(violation.severity)}
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {violation.type.replace(/_/g, ' ').toUpperCase()}
                      </p>
                      <Badge variant={getSeverityColor(violation.severity)} className="text-xs">
                        {violation.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-700 dark:text-gray-300">{violation.message}</p>
                    <div className="flex gap-4 text-xs text-gray-500 dark:text-gray-400">
                      <span>Current: {violation.current_value.toFixed(2)}</span>
                      <span>Limit: {violation.limit_value.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Risk Parameters Summary */}
          {parameters && (
            <div className="space-y-2 pt-2 border-t border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Risk Parameters
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-400">
                <div>Max Daily Loss: {formatPercentage(parameters.max_daily_loss_percentage)}</div>
                <div>Max Drawdown: {formatPercentage(parameters.max_drawdown_percentage)}</div>
                <div>Max Position Size: {formatPercentage(parameters.max_position_size_percentage)}</div>
                <div>Max Positions: {parameters.max_positions_per_strategy}</div>
                {parameters.max_trades_per_day && (
                  <div>Max Trades/Day: {parameters.max_trades_per_day}</div>
                )}
                {parameters.max_loss_per_trade && (
                  <div>Max Loss/Trade: {formatCurrency(parameters.max_loss_per_trade)}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
