export interface WSMessage {
  type: string;
  payload: any;
}

export type WSConnectionStatus = "connecting" | "open" | "closed";

class ResilientWebSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private status: WSConnectionStatus = "closed";
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000; // ms
  private heartbeatInterval = 15000; // ms
  private heartbeatTimer: any = null;
  private listeners: Set<(status: WSConnectionStatus, msg?: WSMessage) => void> = new Set();

  constructor(url = "ws://localhost:8000/api/v1/ws") {
    // Standard URL resolution
    this.url = url;
  }

  public connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.setStatus("connecting");
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.setStatus("open");
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const parsed: WSMessage = JSON.parse(event.data);
          this.triggerListeners("open", parsed);
        } catch {
          // ignore non-json messages
        }
      };

      this.ws.onclose = () => {
        this.handleCloseOrFailure();
      };

      this.ws.onerror = () => {
        this.handleCloseOrFailure();
      };
    } catch {
      this.handleCloseOrFailure();
    }
  }

  private handleCloseOrFailure() {
    this.setStatus("closed");
    this.stopHeartbeat();
    this.ws = null;

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), this.reconnectInterval);
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping", payload: {} }));
      }
    }, this.heartbeatInterval);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private setStatus(newStatus: WSConnectionStatus) {
    this.status = newStatus;
    this.triggerListeners(newStatus);
  }

  private triggerListeners(status: WSConnectionStatus, msg?: WSMessage) {
    this.listeners.forEach((listener) => listener(status, msg));
  }

  public subscribe(listener: (status: WSConnectionStatus, msg?: WSMessage) => void) {
    this.listeners.add(listener);
    // Trigger initial status
    listener(this.status);
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getStatus(): WSConnectionStatus {
    return this.status;
  }

  public disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus("closed");
  }
}

export const socket = new ResilientWebSocket();
export default socket;
