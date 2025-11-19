// Main Application
class OrderBookApp {
    constructor() {
        this.ws = new WebSocketManager('ws://localhost:8081');
        this.orderbook = new OrderBookVisualizer();
        this.chart = new DepthChart('depthChart');

        this.tradesList = document.getElementById('tradesList');
        this.trades = [];
        this.maxTrades = 50;

        this.setupEventListeners();
        this.setupUI();
    }

    setupEventListeners() {
        // WebSocket events
        this.ws.on('l2_update', (data) => this.handleL2Update(data));
        this.ws.on('trade', (data) => this.handleTrade(data));
        this.ws.on('stats', (data) => this.handleStats(data));
        this.ws.on('connection', (data) => this.handleConnection(data));

        // Order entry form
        document.getElementById('submitOrder').addEventListener('click', () => {
            this.submitOrder();
        });

        // Order type change (disable price for market orders)
        document.getElementById('orderType').addEventListener('change', (e) => {
            const priceInput = document.getElementById('orderPrice');
            priceInput.disabled = (e.target.value === 'market');
        });
    }

    setupUI() {
        // Initialize with mock data for testing
        this.generateMockData();
    }

    handleConnection(data) {
        const statusDot = document.getElementById('connectionStatus');
        const statusText = document.getElementById('statusText');

        if (data.connected) {
            statusDot.classList.remove('disconnected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.add('disconnected');
            statusText.textContent = 'Disconnected';
        }
    }

    handleL2Update(data) {
        this.orderbook.updateL2Data(data);
        this.chart.updateData(data.bids, data.asks);

        // Update metrics
        const bbo = this.getBBO(data.bids, data.asks);
        if (bbo) {
            document.getElementById('midPrice').textContent =
                ((bbo.bidPrice + bbo.askPrice) / 2).toFixed(0);

            const imbalance = ((bbo.bidQty - bbo.askQty) / (bbo.bidQty + bbo.askQty)) * 100;
            document.getElementById('imbalance').textContent = imbalance.toFixed(1) + '%';
        }
    }

    handleTrade(data) {
        console.log('Trade received:', data); // Debug log
        this.trades.unshift(data);
        if (this.trades.length > this.maxTrades) {
            this.trades.pop();
        }

        this.renderTrades();
        this.updateTradeMetrics(data);
    }

    handleStats(data) {
        if (data.totalTrades !== undefined) {
            document.getElementById('totalTrades').textContent =
                data.totalTrades.toLocaleString();
        }
        if (data.totalVolume !== undefined) {
            document.getElementById('totalVolume').textContent =
                this.formatQty(data.totalVolume);
        }
        if (data.activeOrders !== undefined) {
            document.getElementById('activeOrders').textContent =
                data.activeOrders.toLocaleString();
        }
    }

    renderTrades() {
        this.tradesList.innerHTML = '';

        this.trades.forEach(trade => {
            const div = document.createElement('div');
            div.className = `trade-item ${trade.side}`;

            // Handle timestamp (detect if nanoseconds or milliseconds)
            let timestamp = trade.timestamp;
            if (timestamp > 1e12 && timestamp < 1e15) {
                // Likely milliseconds, do nothing
            } else if (timestamp >= 1e15) {
                // Likely nanoseconds, convert to milliseconds
                timestamp = timestamp / 1000000;
            } else if (timestamp < 1e12) {
                // Likely seconds, convert to milliseconds
                timestamp = timestamp * 1000;
            }

            const time = new Date(timestamp).toLocaleTimeString();

            div.innerHTML = `
                <div class="trade-price">${this.formatPrice(trade.price)}</div>
                <div class="trade-qty">${this.formatQty(trade.quantity)}</div>
                <div class="trade-time">${time}</div>
            `;

            this.tradesList.appendChild(div);
        });
    }

    updateTradeMetrics(trade) {
        document.getElementById('lastPrice').textContent = this.formatPrice(trade.price);

        // Increment total trades and volume
        const currentTrades = parseInt(document.getElementById('totalTrades').textContent.replace(/,/g, '')) || 0;
        const currentVolume = this.parseFormattedQty(document.getElementById('totalVolume').textContent) || 0;

        document.getElementById('totalTrades').textContent = (currentTrades + 1).toLocaleString();
        document.getElementById('totalVolume').textContent = this.formatQty(currentVolume + trade.quantity);
    }

    submitOrder() {
        const side = document.getElementById('orderSide').value;
        const type = document.getElementById('orderType').value;
        const price = parseInt(document.getElementById('orderPrice').value) || 0;
        const qty = parseInt(document.getElementById('orderQty').value) || 0;

        if (qty <= 0) {
            alert('Invalid quantity');
            return;
        }

        if (type === 'limit' && price <= 0) {
            alert('Invalid price');
            return;
        }

        const success = this.ws.submitOrder(side, type, price, qty);

        if (success) {
            // Show success animation
            const btn = document.getElementById('submitOrder');
            const originalText = btn.innerHTML;
            btn.textContent = '✓ Submitted';
            btn.classList.add('success');

            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.remove('success');
            }, 1000);

            // Do NOT clear form to allow rapid entry/adjustments
            // document.getElementById('orderPrice').value = '';
            // document.getElementById('orderQty').value = '';
        } else {
            alert('Not connected to server');
        }
    }

    getBBO(bids, asks) {
        if (!bids || !asks || bids.length === 0 || asks.length === 0) {
            return null;
        }
        return {
            bidPrice: bids[0].price,
            bidQty: bids[0].qty,
            askPrice: asks[0].price,
            askQty: asks[0].qty
        };
    }

    formatPrice(price) {
        return price.toLocaleString('en-US');
    }

    formatQty(qty) {
        if (qty >= 1000000) return (qty / 1000000).toFixed(2) + 'M';
        if (qty >= 1000) return (qty / 1000).toFixed(1) + 'K';
        return qty.toLocaleString();
    }

    parseFormattedQty(str) {
        if (str.endsWith('M')) {
            return parseFloat(str) * 1000000;
        } else if (str.endsWith('K')) {
            return parseFloat(str) * 1000;
        }
        return parseInt(str.replace(/,/g, '')) || 0;
    }

    // Generate mock data for demonstration when not connected
    generateMockData() {
        const basePrice = 10000;
        const bids = [];
        const asks = [];

        for (let i = 0; i < 10; i++) {
            bids.push({
                price: basePrice - i * 10,
                qty: Math.floor(Math.random() * 1000) + 100,
                orders: Math.floor(Math.random() * 5) + 1
            });
            asks.push({
                price: basePrice + 10 + i * 10,
                qty: Math.floor(Math.random() * 1000) + 100,
                orders: Math.floor(Math.random() * 5) + 1
            });
        }

        this.handleL2Update({ bids, asks });

        // Periodically update mock data
        setInterval(() => {
            if (this.ws.ws && this.ws.ws.readyState !== WebSocket.OPEN) {
                this.generateMockData();
            }
        }, 2000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new OrderBookApp();
});
