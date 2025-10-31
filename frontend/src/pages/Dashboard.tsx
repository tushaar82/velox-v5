/**
 * Main trading dashboard page.
 */
'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { apiService } from '../services/api';
import { useWebSocket } from '../services/websocket';
import type {
  StrategyInstance,
  Position,
  PerformanceMetrics,
  RiskMetrics as RiskMetricsType,
  RiskParameters,
  EquityPoint,
  DailyPnL,
  DrawdownPoint,
  WebSocketMessage,
} from '../types';
import { StrategyCard } from '../components/dashboard/StrategyCard';
import { PositionTable } from '../components/dashboard/PositionTable';
import { RiskMetrics } from '../components/dashboard/RiskMetrics';
import { EquityChart } from '../components/charts/EquityChart';
import { PnLChart } from '../components/charts/PnLChart';
import { DrawdownChart } from '../components/charts/DrawdownChart';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { RefreshCw, Settings, Activity } from 'lucide-react';

export default function Dashboard() {
  // State
  const [strategies, setStrategies] = useState<StrategyInstance[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<number | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<Record<number, PerformanceMetrics>>({});
  const [riskMetrics, setRiskMetrics] = useState<RiskMetricsType | null>(null);
  const [riskParameters, setRiskParameters] = useState<RiskParameters | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [dailyPnL, setDailyPnL] = useState<DailyPnL[]>([]);
  const [drawdown, setDrawdown] = useState<DrawdownPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);

  // WebSocket
  const ws = useWebSocket(selectedStrategyId || undefined);

  // Load initial data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);

      // Load strategies
      const strategiesData = await apiService.getStrategyInstances();
      setStrategies(strategiesData);

      // Select first strategy if none selected
      if (!selectedStrategyId && strategiesData.length > 0) {
        setSelectedStrategyId(strategiesData[0].id);
      }

      // Load positions
      if (selectedStrategyId) {
        const positionsData = await apiService.getPositions(selectedStrategyId);
        setPositions(positionsData);

        // Load performance metrics
        const metrics = await apiService.getPerformanceMetrics(selectedStrategyId);
        setPerformanceMetrics((prev) => ({ ...prev, [selectedStrategyId]: metrics }));

        // Load risk metrics
        const risk = await apiService.getRiskMetrics(selectedStrategyId);
        setRiskMetrics(risk);

        // Load charts data
        const [equity, pnl, dd] = await Promise.all([
          apiService.getEquityCurve(selectedStrategyId),
          apiService.getDailyPnL(selectedStrategyId),
          apiService.getDrawdown(selectedStrategyId),
        ]);

        setEquityCurve(equity);
        setDailyPnL(pnl);
        setDrawdown(dd);
      }

      // Load risk parameters
      try {
        const params = await apiService.getRiskParameters();
        setRiskParameters(params);
      } catch (error) {
        console.error('Risk parameters not set:', error);
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedStrategyId]);

  // Setup WebSocket handlers
  useEffect(() => {
    if (!selectedStrategyId) return;

    const handleConnection = (message: WebSocketMessage) => {
      console.log('WebSocket connection status:', message);
      setWsConnected(message.type === 'connected');
    };

    const handleTickUpdate = (message: WebSocketMessage) => {
      console.log('Tick update:', message.data);
      // Update positions with latest prices if needed
    };

    const handlePositionUpdate = (message: WebSocketMessage) => {
      console.log('Position update:', message.data);
      // Refresh positions
      if (selectedStrategyId) {
        apiService.getPositions(selectedStrategyId).then(setPositions);
      }
    };

    const handleOrderUpdate = (message: WebSocketMessage) => {
      console.log('Order update:', message.data);
      // Refresh positions when orders are filled
      if (selectedStrategyId) {
        apiService.getPositions(selectedStrategyId).then(setPositions);
      }
    };

    const handlePerformanceUpdate = (message: WebSocketMessage) => {
      console.log('Performance update:', message.data);
      // Update performance metrics
      if (selectedStrategyId && message.data) {
        setPerformanceMetrics((prev) => ({
          ...prev,
          [selectedStrategyId]: message.data,
        }));
      }
    };

    const handleRiskAlert = (message: WebSocketMessage) => {
      console.log('Risk alert:', message);
      // Show notification or refresh risk metrics
      if (selectedStrategyId) {
        apiService.getRiskMetrics(selectedStrategyId).then(setRiskMetrics);
      }
    };

    // Register handlers
    ws.on('connection', handleConnection);
    ws.on('tick_update', handleTickUpdate);
    ws.on('position_update', handlePositionUpdate);
    ws.on('order_update', handleOrderUpdate);
    ws.on('performance_update', handlePerformanceUpdate);
    ws.on('risk_alert', handleRiskAlert);

    // Connect
    ws.connect();

    // Setup ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.isConnected()) {
        ws.ping();
      }
    }, 30000); // Ping every 30 seconds

    return () => {
      clearInterval(pingInterval);
      ws.off('connection', handleConnection);
      ws.off('tick_update', handleTickUpdate);
      ws.off('position_update', handlePositionUpdate);
      ws.off('order_update', handleOrderUpdate);
      ws.off('performance_update', handlePerformanceUpdate);
      ws.off('risk_alert', handleRiskAlert);
      ws.disconnect();
    };
  }, [selectedStrategyId, ws]);

  // Load data on mount and when selected strategy changes
  useEffect(() => {
    apiService.loadToken();
    loadData();
  }, [loadData]);

  // Event handlers
  const handleStartStrategy = async (strategyId: number) => {
    try {
      await apiService.startStrategyInstance(strategyId);
      await loadData();
    } catch (error) {
      console.error('Error starting strategy:', error);
    }
  };

  const handleStopStrategy = async (strategyId: number) => {
    try {
      await apiService.stopStrategyInstance(strategyId);
      await loadData();
    } catch (error) {
      console.error('Error stopping strategy:', error);
    }
  };

  const handleClosePosition = async (positionId: number) => {
    try {
      await apiService.closePosition(positionId);
      await loadData();
    } catch (error) {
      console.error('Error closing position:', error);
    }
  };

  const handleRefresh = () => {
    loadData();
  };

  if (loading && strategies.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600 dark:text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const selectedStrategy = strategies.find((s) => s.id === selectedStrategyId);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Velox Trading Dashboard
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Real-time algorithmic trading analytics
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={wsConnected ? 'success' : 'secondary'}>
                <Activity className="w-3 h-3 mr-1" />
                {wsConnected ? 'Live' : 'Disconnected'}
              </Badge>
              <Button variant="outline" size="sm" onClick={handleRefresh}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </Button>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Strategy Cards Grid */}
          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Active Strategies
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {strategies.map((strategy) => (
                <div
                  key={strategy.id}
                  onClick={() => setSelectedStrategyId(strategy.id)}
                  className={`cursor-pointer transition-transform ${
                    selectedStrategyId === strategy.id ? 'ring-2 ring-blue-500 rounded-lg' : ''
                  }`}
                >
                  <StrategyCard
                    strategy={strategy}
                    metrics={performanceMetrics[strategy.id]}
                    onStart={() => handleStartStrategy(strategy.id)}
                    onStop={() => handleStopStrategy(strategy.id)}
                    onViewDetails={() => setSelectedStrategyId(strategy.id)}
                  />
                </div>
              ))}
            </div>
          </section>

          {/* Selected Strategy Details */}
          {selectedStrategy && (
            <>
              {/* Risk Metrics */}
              <section>
                {riskMetrics && (
                  <RiskMetrics metrics={riskMetrics} parameters={riskParameters || undefined} />
                )}
              </section>

              {/* Charts Row 1 */}
              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {equityCurve.length > 0 && <EquityChart data={equityCurve} />}
                {dailyPnL.length > 0 && <PnLChart data={dailyPnL} />}
              </section>

              {/* Charts Row 2 */}
              <section>
                {drawdown.length > 0 && <DrawdownChart data={drawdown} />}
              </section>

              {/* Positions Table */}
              <section>
                <PositionTable
                  positions={positions}
                  onClosePosition={handleClosePosition}
                  showActions={true}
                />
              </section>
            </>
          )}

          {/* Empty State */}
          {strategies.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-600 dark:text-gray-400 text-lg">
                No strategies found. Create a strategy to get started.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
