/**
 * Position table component displaying open positions.
 */
'use client';

import React from 'react';
import type { Position } from '../../types';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { X, TrendingUp, TrendingDown } from 'lucide-react';
import { format } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

interface PositionTableProps {
  positions: Position[];
  onClosePosition?: (positionId: number) => void;
  showActions?: boolean;
}

export function PositionTable({ positions, onClosePosition, showActions = true }: PositionTableProps) {
  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercentage = (position: Position) => {
    const pnlPercentage = ((position.current_price - position.entry_price) / position.entry_price) * 100;
    const adjusted = position.side === 'sell' ? -pnlPercentage : pnlPercentage;
    return `${adjusted >= 0 ? '+' : ''}${adjusted.toFixed(2)}%`;
  };

  const getPnLColor = (pnl: number) => {
    return pnl >= 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold';
  };

  const getSideColor = (side: string) => {
    return side === 'buy' ? 'success' : 'destructive';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'success';
      case 'closed':
        return 'secondary';
      case 'partial':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No open positions
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Open Positions ({positions.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead>Side</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead className="text-right">Entry Price</TableHead>
              <TableHead className="text-right">Current Price</TableHead>
              <TableHead className="text-right">Unrealized P&L</TableHead>
              <TableHead className="text-right">P&L %</TableHead>
              <TableHead>Opened At</TableHead>
              <TableHead>Status</TableHead>
              {showActions && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {positions.map((position) => (
              <TableRow key={position.id}>
                <TableCell className="font-medium">{position.symbol}</TableCell>
                <TableCell>
                  <Badge variant={getSideColor(position.side)}>
                    {position.side === 'buy' ? (
                      <TrendingUp className="w-3 h-3 mr-1 inline" />
                    ) : (
                      <TrendingDown className="w-3 h-3 mr-1 inline" />
                    )}
                    {position.side.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell>
                  {position.quantity}
                  {position.remaining_quantity !== position.quantity && (
                    <span className="text-xs text-gray-500 ml-1">
                      ({position.remaining_quantity} rem)
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right">{formatCurrency(position.entry_price)}</TableCell>
                <TableCell className="text-right">{formatCurrency(position.current_price)}</TableCell>
                <TableCell className={`text-right ${getPnLColor(position.unrealized_pnl)}`}>
                  {formatCurrency(position.unrealized_pnl)}
                </TableCell>
                <TableCell className={`text-right ${getPnLColor(position.unrealized_pnl)}`}>
                  {formatPercentage(position)}
                </TableCell>
                <TableCell className="text-sm">
                  {format(new Date(position.opened_at), 'MMM dd, HH:mm')}
                </TableCell>
                <TableCell>
                  <Badge variant={getStatusColor(position.status)}>
                    {position.status.toUpperCase()}
                  </Badge>
                </TableCell>
                {showActions && (
                  <TableCell className="text-right">
                    {position.status === 'open' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onClosePosition?.(position.id)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <X className="w-4 h-4 mr-1" />
                        Close
                      </Button>
                    )}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
