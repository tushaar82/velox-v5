/**
 * WebSocket client for real-time updates.
 */
import { io, Socket } from 'socket.io-client';
import type { WebSocketMessage } from '../types';

export type WebSocketEventHandler = (message: WebSocketMessage) => void;

class WebSocketClient {
  private socket: Socket | null = null;
  private token: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private handlers: Map<string, Set<WebSocketEventHandler>> = new Map();
  private strategyId: number | null = null;
  private isConnecting = false;

  constructor() {
    // Load token from localStorage
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
  }

  /**
   * Connect to WebSocket server.
   */
  connect(strategyId?: number) {
    if (this.isConnecting || this.socket?.connected) {
      console.log('WebSocket already connecting or connected');
      return;
    }

    if (!this.token) {
      console.error('No auth token available for WebSocket connection');
      return;
    }

    this.isConnecting = true;
    this.strategyId = strategyId || null;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const path = strategyId ? `/ws/strategy/${strategyId}` : '/ws/live';

    console.log(`Connecting to WebSocket: ${wsUrl}${path}`);

    this.socket = io(wsUrl, {
      path,
      query: { token: this.token },
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      reconnectionDelayMax: 5000,
    });

    this.setupEventHandlers();
    this.isConnecting = false;
  }

  /**
   * Disconnect from WebSocket server.
   */
  disconnect() {
    if (this.socket) {
      console.log('Disconnecting WebSocket');
      this.socket.disconnect();
      this.socket = null;
      this.strategyId = null;
      this.reconnectAttempts = 0;
    }
  }

  /**
   * Check if connected.
   */
  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  /**
   * Set auth token.
   */
  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  /**
   * Setup event handlers for WebSocket.
   */
  private setupEventHandlers() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connection', { type: 'connected', message: 'Connected to WebSocket' });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('connection', { type: 'connected', message: `Disconnected: ${reason}` });
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached');
        this.disconnect();
      }
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    // Handle incoming messages
    this.socket.on('message', (data: string) => {
      try {
        const message: WebSocketMessage = JSON.parse(data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    });

    // Alternative event listener for direct event emissions
    this.socket.onAny((eventName: string, ...args: any[]) => {
      if (eventName === 'message' || eventName === 'connect' || eventName === 'disconnect' || eventName === 'connect_error' || eventName === 'error') {
        // Already handled above
        return;
      }

      console.log('WebSocket event:', eventName, args);
    });
  }

  /**
   * Handle incoming WebSocket message.
   */
  private handleMessage(message: WebSocketMessage) {
    console.log('WebSocket message received:', message.type);

    // Emit to specific message type handlers
    this.emit(message.type, message);

    // Emit to global message handler
    this.emit('message', message);
  }

  /**
   * Emit event to registered handlers.
   */
  private emit(event: string, message: WebSocketMessage) {
    const handlers = this.handlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message);
        } catch (error) {
          console.error('Error in WebSocket handler:', error);
        }
      });
    }
  }

  /**
   * Subscribe to WebSocket events.
   */
  on(event: string, handler: WebSocketEventHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  /**
   * Unsubscribe from WebSocket events.
   */
  off(event: string, handler: WebSocketEventHandler) {
    const handlers = this.handlers.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Send ping to keep connection alive.
   */
  ping() {
    if (this.socket?.connected) {
      this.socket.emit('ping');
    }
  }

  /**
   * Send message to server.
   */
  send(message: any) {
    if (this.socket?.connected) {
      this.socket.emit('message', JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();

// Hook for using WebSocket in React components
export function useWebSocket(strategyId?: number) {
  if (typeof window === 'undefined') {
    // SSR guard
    return {
      connect: () => {},
      disconnect: () => {},
      on: () => {},
      off: () => {},
      isConnected: () => false,
      send: () => {},
      ping: () => {},
    };
  }

  return {
    connect: () => wsClient.connect(strategyId),
    disconnect: () => wsClient.disconnect(),
    on: (event: string, handler: WebSocketEventHandler) => wsClient.on(event, handler),
    off: (event: string, handler: WebSocketEventHandler) => wsClient.off(event, handler),
    isConnected: () => wsClient.isConnected(),
    send: (message: any) => wsClient.send(message),
    ping: () => wsClient.ping(),
  };
}
