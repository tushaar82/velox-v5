/**
 * Daily P&L chart component.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend } from 'recharts';
import { format } from 'date-fns';
import type { DailyPnL } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

interface PnLChartProps {
  data: DailyPnL[];
  title?: string;
  height?: number;
}

export function PnLChart({ data, title = 'Daily P&L', height = 400 }: PnLChartProps) {
  // Format data for recharts
  const chartData = data.map((point) => ({
    date: point.date,
    pnl: point.pnl,
    trades: point.trades,
    winningTrades: point.winning_trades,
    losingTrades: point.losing_trades,
    formattedDate: format(new Date(point.date), 'MMM dd'),
  }));

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Custom tooltip to show more details
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-gray-800 p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 dark:text-gray-100">
            {format(new Date(data.date), 'MMM dd, yyyy')}
          </p>
          <p className={`text-lg font-bold ${data.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(data.pnl)}
          </p>
          <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            <p>Total Trades: {data.trades}</p>
            <p className="text-green-600">Winning: {data.winningTrades}</p>
            <p className="text-red-600">Losing: {data.losingTrades}</p>
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
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
            <XAxis
              dataKey="formattedDate"
              className="text-gray-600 dark:text-gray-400"
            />
            <YAxis
              tickFormatter={formatCurrency}
              className="text-gray-600 dark:text-gray-400"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar dataKey="pnl" name="Daily P&L" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
