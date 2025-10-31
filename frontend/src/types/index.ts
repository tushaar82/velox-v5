/**
 * Type definitions for the Velox trading platform frontend.
 */

// User types
export interface User {
  id: number;
  email: string;
  full_name?: string;
  role: 'admin' | 'trader' | 'analyst';
  is_active: boolean;
  created_at: string;
}

// Strategy types
export interface Strategy {
  id: number;
  name: string;
  description: string;
  strategy_type: string;
  parameters: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StrategyInstance {
  id: number;
  user_id: number;
  strategy_id: number;
  name: string;
  status: 'running' | 'stopped' | 'paused' | 'error';
  trading_mode: 'live' | 'paper';
  symbol: string;
  timeframe: string;
  parameters: Record<string, any>;
  max_position_size: number;
  total_pnl: number;
  created_at: string;
  updated_at: string;
  started_at?: string;
  stopped_at?: string;
}

// Trading types
export enum OrderSide {
  BUY = 'buy',
  SELL = 'sell',
}

export enum OrderStatus {
  PENDING = 'pending',
  OPEN = 'open',
  FILLED = 'filled',
  PARTIALLY_FILLED = 'partially_filled',
  CANCELLED = 'cancelled',
  REJECTED = 'rejected',
  EXPIRED = 'expired',
}

export interface TradeOrder {
  id: number;
  strategy_instance_id: number;
  symbol: string;
  side: OrderSide;
  order_type: string;
  quantity: number;
  price?: number;
  stop_price?: number;
  status: OrderStatus;
  filled_quantity: number;
  average_fill_price?: number;
  commission?: number;
  created_at: string;
  updated_at: string;
  filled_at?: string;
}

export enum PositionStatus {
  OPEN = 'open',
  CLOSED = 'closed',
  PARTIAL = 'partial',
}

export interface Position {
  id: number;
  strategy_instance_id: number;
  symbol: string;
  side: OrderSide;
  entry_price: number;
  current_price: number;
  quantity: number;
  remaining_quantity: number;
  status: PositionStatus;
  realized_pnl: number;
  unrealized_pnl: number;
  commission: number;
  opened_at: string;
  closed_at?: string;
  max_price?: number;
  min_price?: number;
}

export interface TrailingStoploss {
  id: number;
  position_id: number;
  trailing_percentage: number;
  trailing_amount?: number;
  highest_price: number;
  current_stop_price: number;
  is_active: boolean;
  is_triggered: boolean;
  created_at: string;
  triggered_at?: string;
}

// Market data types
export interface Tick {
  id: number;
  symbol: string;
  price: number;
  volume: number;
  bid?: number;
  ask?: number;
  timestamp: string;
}

export interface Candle {
  id: number;
  symbol: string;
  timeframe: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// Risk types
export interface RiskParameters {
  id: number;
  user_id: number;
  max_daily_loss_percentage: number;
  max_daily_loss_amount?: number;
  max_position_size_percentage: number;
  max_positions_per_strategy: number;
  max_drawdown_percentage: number;
  max_trades_per_day?: number;
  max_loss_per_trade?: number;
}

export interface RiskMetrics {
  daily_pnl: number;
  drawdown_amount: number;
  drawdown_percentage: number;
  open_positions_count: number;
  is_within_limits: boolean;
  violations: RiskViolation[];
}

export interface RiskViolation {
  type: string;
  current_value: number;
  limit_value: number;
  severity: 'info' | 'warning' | 'critical';
  message: string;
}

// Analytics types
export interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_profit: number;
  total_loss: number;
  profit_factor: number;
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  average_trade_duration: number;
  roi_percentage: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  max_drawdown_percentage: number;
  current_streak: number;
  longest_winning_streak: number;
  longest_losing_streak: number;
  total_commission: number;
  net_pnl: number;
  starting_equity: number;
  current_equity: number;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  cumulative_pnl: number;
}

export interface DailyPnL {
  date: string;
  pnl: number;
  trades: number;
  winning_trades: number;
  losing_trades: number;
}

export interface DrawdownPoint {
  timestamp: string;
  equity: number;
  peak_equity: number;
  drawdown: number;
  drawdown_percentage: number;
}

// WebSocket message types
export interface WebSocketMessage {
  type: 'connected' | 'tick_update' | 'position_update' | 'order_update' | 'performance_update' | 'risk_alert' | 'pong';
  strategy_id?: number;
  data?: any;
  timestamp?: string;
  severity?: 'info' | 'warning' | 'critical';
  message?: string;
}

// Broker types
export interface BrokerAccount {
  id: number;
  user_id: number;
  broker_type: string;
  account_name: string;
  account_id: string;
  is_active: boolean;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

export interface BrokerBalance {
  id: number;
  broker_account_id: number;
  available_cash: number;
  total_cash: number;
  margin_used: number;
  margin_available: number;
  updated_at: string;
}

export interface BrokerConnectionTest {
  success: boolean;
  broker_name: string;
  message: string;
}

// API response types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  status?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
