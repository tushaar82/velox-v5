/**
 * Drawdown chart component.
 */
import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { format } from 'date-fns';
import type { DrawdownPoint } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

interface DrawdownChartProps {
  data: DrawdownPoint[];
  title?: string;
  height?: number;
}

export function DrawdownChart({ data, title = 'Drawdown', height = 400 }: DrawdownChartProps) {
  // Format data for recharts
  const chartData = data.map((point) => ({
    timestamp: new Date(point.timestamp).getTime(),
    drawdown_percentage: point.drawdown_percentage,
    drawdown: point.drawdown,
    equity: point.equity,
    peak_equity: point.peak_equity,
    formattedDate: format(new Date(point.timestamp), 'MMM dd, HH:mm'),
  }));

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatXAxis = (timestamp: number) => {
    return format(new Date(timestamp), 'MMM dd');
  };

  // Custom tooltip to show more details
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-gray-800 p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 dark:text-gray-100">
            {format(new Date(data.timestamp), 'MMM dd, yyyy HH:mm')}
          </p>
          <div className="mt-2 space-y-1">
            <p className="text-red-600 font-bold">
              Drawdown: {formatPercentage(data.drawdown_percentage)}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Amount: {formatCurrency(data.drawdown)}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Current Equity: {formatCurrency(data.equity)}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Peak Equity: {formatCurrency(data.peak_equity)}
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <defs>
              <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXAxis}
              className="text-gray-600 dark:text-gray-400"
            />
            <YAxis
              tickFormatter={formatPercentage}
              className="text-gray-600 dark:text-gray-400"
              reversed
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Area
              type="monotone"
              dataKey="drawdown_percentage"
              stroke="#ef4444"
              fill="url(#colorDrawdown)"
              name="Drawdown %"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
