/**
 * Equity curve chart component.
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { format } from 'date-fns';
import type { EquityPoint } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

interface EquityChartProps {
  data: EquityPoint[];
  title?: string;
  height?: number;
}

export function EquityChart({ data, title = 'Equity Curve', height = 400 }: EquityChartProps) {
  // Format data for recharts
  const chartData = data.map((point) => ({
    timestamp: new Date(point.timestamp).getTime(),
    equity: point.equity,
    cumulative_pnl: point.cumulative_pnl,
    date: format(new Date(point.timestamp), 'MMM dd, HH:mm'),
  }));

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatXAxis = (timestamp: number) => {
    return format(new Date(timestamp), 'MMM dd');
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXAxis}
              className="text-gray-600 dark:text-gray-400"
            />
            <YAxis
              tickFormatter={formatCurrency}
              className="text-gray-600 dark:text-gray-400"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
              labelFormatter={(timestamp) => format(new Date(timestamp), 'MMM dd, yyyy HH:mm')}
              formatter={(value: number, name: string) => [
                formatCurrency(value),
                name === 'equity' ? 'Equity' : 'Cumulative P&L',
              ]}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="equity"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              name="Equity"
            />
            <Line
              type="monotone"
              dataKey="cumulative_pnl"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="Cumulative P&L"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
