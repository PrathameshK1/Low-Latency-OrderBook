// WebSocket Connection Manager
class WebSocketManager {
    constructor(url = 'ws://localhost:8081') {
        this.url = url;
        this.ws = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.reconnectAttempts = 0;
        this.callbacks = {
            'l2_update': [],
            'trade': [],
            'order_submitted': [],
            'stress_test_start': [],
            'stress_test_end': [],
            'stats': [],
            'performance': [],
            'connection': []
        };
        this.connect();
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectDelay = 1000;
                this.reconnectAttempts = 0;
                this.triggerCallbacks('connection', { connected: true });
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('Failed to parse message:', e);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.triggerCallbacks('connection', { connected: false });
                this.scheduleReconnect();
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(
            this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts),
            this.maxReconnectDelay
        );

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    handleMessage(data) {
        const type = data.type;
        if (this.callbacks[type]) {
            this.triggerCallbacks(type, data);
        } else {
            // Log unhandled message types for debugging
            console.log('Unhandled message type:', type, data);
        }
    }

    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }

    triggerCallbacks(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(cb => cb(data));
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    submitOrder(side, type, price, quantity) {
        return this.send({
            type: 'submit_order',
            side: side,
            orderType: type,
            price: price,
            quantity: quantity
        });
    }
}

// Export for use in other files
window.WebSocketManager = WebSocketManager;
