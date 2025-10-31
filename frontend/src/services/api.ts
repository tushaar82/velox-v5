/**
 * API service for making HTTP requests to the backend.
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import type {
  User,
  Strategy,
  StrategyInstance,
  Position,
  TradeOrder,
  TrailingStoploss,
  RiskParameters,
  RiskMetrics,
  PerformanceMetrics,
  EquityPoint,
  DailyPnL,
  DrawdownPoint,
  Tick,
  Candle,
  ApiResponse,
  PaginatedResponse,
} from '../types';

class ApiService {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized - clear token and redirect to login
          this.clearToken();
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Token management
  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  loadToken() {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token) {
        this.token = token;
      }
    }
  }

  // Generic request method
  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.request(config);
      return response.data;
    } catch (error: any) {
      throw error.response?.data || error.message;
    }
  }

  // ============= Authentication =============

  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await this.request<{ access_token: string; token_type: string }>({
      method: 'POST',
      url: '/api/v1/auth/login',
      data: formData,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    this.setToken(response.access_token);
    return response;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>({
      method: 'GET',
      url: '/api/v1/auth/me',
    });
  }

  async logout() {
    this.clearToken();
  }

  // ============= Strategies =============

  async getStrategies(): Promise<Strategy[]> {
    return this.request<Strategy[]>({
      method: 'GET',
      url: '/api/v1/strategies',
    });
  }

  async getStrategy(id: number): Promise<Strategy> {
    return this.request<Strategy>({
      method: 'GET',
      url: `/api/v1/strategies/${id}`,
    });
  }

  async getStrategyInstances(): Promise<StrategyInstance[]> {
    return this.request<StrategyInstance[]>({
      method: 'GET',
      url: '/api/v1/strategies/instances',
    });
  }

  async getStrategyInstance(id: number): Promise<StrategyInstance> {
    return this.request<StrategyInstance>({
      method: 'GET',
      url: `/api/v1/strategies/instances/${id}`,
    });
  }

  async createStrategyInstance(data: {
    strategy_id: number;
    name: string;
    symbol: string;
    timeframe: string;
    parameters: Record<string, any>;
    max_position_size: number;
    trading_mode: 'live' | 'paper';
  }): Promise<StrategyInstance> {
    return this.request<StrategyInstance>({
      method: 'POST',
      url: '/api/v1/strategies/instances',
      data,
    });
  }

  async startStrategyInstance(id: number): Promise<StrategyInstance> {
    return this.request<StrategyInstance>({
      method: 'POST',
      url: `/api/v1/strategies/instances/${id}/start`,
    });
  }

  async stopStrategyInstance(id: number): Promise<StrategyInstance> {
    return this.request<StrategyInstance>({
      method: 'POST',
      url: `/api/v1/strategies/instances/${id}/stop`,
    });
  }

  async switchTradingMode(
    id: number,
    mode: 'live' | 'paper',
    force: boolean = false
  ): Promise<{ success: boolean; message?: string }> {
    return this.request<{ success: boolean; message?: string }>({
      method: 'POST',
      url: `/api/v1/strategies/instances/${id}/switch-mode`,
      data: { mode, force },
    });
  }

  // ============= Positions =============

  async getPositions(strategyInstanceId?: number): Promise<Position[]> {
    return this.request<Position[]>({
      method: 'GET',
      url: '/api/v1/trading/positions',
      params: strategyInstanceId ? { strategy_instance_id: strategyInstanceId } : undefined,
    });
  }

  async getPosition(id: number): Promise<Position> {
    return this.request<Position>({
      method: 'GET',
      url: `/api/v1/trading/positions/${id}`,
    });
  }

  async closePosition(id: number): Promise<Position> {
    return this.request<Position>({
      method: 'POST',
      url: `/api/v1/trading/positions/${id}/close`,
    });
  }

  // ============= Trailing Stoploss =============

  async createTrailingStoploss(
    positionId: number,
    trailingPercentage: number,
    trailingAmount?: number
  ): Promise<TrailingStoploss> {
    return this.request<TrailingStoploss>({
      method: 'POST',
      url: `/api/v1/trading/positions/${positionId}/trailing-stoploss`,
      data: {
        trailing_percentage: trailingPercentage,
        trailing_amount: trailingAmount,
      },
    });
  }

  async getTrailingStoploss(positionId: number): Promise<TrailingStoploss> {
    return this.request<TrailingStoploss>({
      method: 'GET',
      url: `/api/v1/trading/positions/${positionId}/trailing-stoploss`,
    });
  }

  async deleteTrailingStoploss(positionId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>({
      method: 'DELETE',
      url: `/api/v1/trading/positions/${positionId}/trailing-stoploss`,
    });
  }

  // ============= Orders =============

  async getOrders(strategyInstanceId?: number): Promise<TradeOrder[]> {
    return this.request<TradeOrder[]>({
      method: 'GET',
      url: '/api/v1/trading/orders',
      params: strategyInstanceId ? { strategy_instance_id: strategyInstanceId } : undefined,
    });
  }

  async cancelOrder(id: number): Promise<TradeOrder> {
    return this.request<TradeOrder>({
      method: 'POST',
      url: `/api/v1/trading/orders/${id}/cancel`,
    });
  }

  // ============= Risk Management =============

  async getRiskParameters(): Promise<RiskParameters> {
    return this.request<RiskParameters>({
      method: 'GET',
      url: '/api/v1/risk/parameters',
    });
  }

  async updateRiskParameters(data: Partial<RiskParameters>): Promise<RiskParameters> {
    return this.request<RiskParameters>({
      method: 'POST',
      url: '/api/v1/risk/parameters',
      data,
    });
  }

  async getRiskMetrics(strategyInstanceId: number): Promise<RiskMetrics> {
    return this.request<RiskMetrics>({
      method: 'GET',
      url: `/api/v1/risk/metrics/${strategyInstanceId}`,
    });
  }

  async closeAllPositions(strategyInstanceId: number, reason: string = 'Manual closure'): Promise<{
    message: string;
    strategy_instance_id: number;
    closed_count: number;
  }> {
    return this.request<{ message: string; strategy_instance_id: number; closed_count: number }>({
      method: 'POST',
      url: `/api/v1/risk/close-all-positions/${strategyInstanceId}`,
      data: { reason },
    });
  }

  // ============= Analytics =============

  async getPerformanceMetrics(strategyInstanceId: number): Promise<PerformanceMetrics> {
    return this.request<PerformanceMetrics>({
      method: 'GET',
      url: `/api/v1/analytics/performance/${strategyInstanceId}`,
    });
  }

  async getEquityCurve(
    strategyInstanceId: number,
    startDate?: string,
    endDate?: string
  ): Promise<EquityPoint[]> {
    return this.request<EquityPoint[]>({
      method: 'GET',
      url: `/api/v1/analytics/equity-curve/${strategyInstanceId}`,
      params: { start_date: startDate, end_date: endDate },
    });
  }

  async getDailyPnL(
    strategyInstanceId: number,
    startDate?: string,
    endDate?: string
  ): Promise<DailyPnL[]> {
    return this.request<DailyPnL[]>({
      method: 'GET',
      url: `/api/v1/analytics/daily-pnl/${strategyInstanceId}`,
      params: { start_date: startDate, end_date: endDate },
    });
  }

  async getDrawdown(
    strategyInstanceId: number,
    startDate?: string,
    endDate?: string
  ): Promise<DrawdownPoint[]> {
    return this.request<DrawdownPoint[]>({
      method: 'GET',
      url: `/api/v1/analytics/drawdown/${strategyInstanceId}`,
      params: { start_date: startDate, end_date: endDate },
    });
  }

  async createPerformanceSnapshot(strategyInstanceId: number): Promise<{ message: string; snapshot_id: number }> {
    return this.request<{ message: string; snapshot_id: number }>({
      method: 'POST',
      url: `/api/v1/analytics/snapshot/${strategyInstanceId}`,
    });
  }

  // ============= Market Data =============

  async getLatestTick(symbol: string): Promise<Tick> {
    return this.request<Tick>({
      method: 'GET',
      url: `/api/v1/market-data/tick/${symbol}`,
    });
  }

  async getCandles(
    symbol: string,
    timeframe: string,
    limit: number = 100
  ): Promise<Candle[]> {
    return this.request<Candle[]>({
      method: 'GET',
      url: `/api/v1/market-data/candles/${symbol}`,
      params: { timeframe, limit },
    });
  }
}

// Export singleton instance
export const apiService = new ApiService();
