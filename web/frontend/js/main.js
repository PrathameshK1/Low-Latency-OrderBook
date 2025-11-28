// Main Application
class OrderBookApp {
    constructor() {
        this.ws = new WebSocketManager('ws://localhost:8081');
        this.orderbook = new OrderBookVisualizer();
        this.chart = new DepthChart('depthChart');
        this.analytics = new MarketAnalytics();

        this.tradesList = document.getElementById('tradesList');
        this.manualTradesList = document.getElementById('manualTradesList');
        this.trades = [];
        this.manualTrades = [];
        this.maxTrades = 50;
        this.maxManualTrades = 20;
        this.currentTradeTab = 'all';
        this.manualOrderCount = 0;

        this.setupEventListeners();
        this.setupUI();
    }

    setupEventListeners() {
        // WebSocket events
        this.ws.on('l2_update', (data) => this.handleL2Update(data));
        this.ws.on('trade', (data) => this.handleTrade(data));
        this.ws.on('order_submitted', (data) => this.handleOrderSubmitted(data));
        this.ws.on('stress_test_start', (data) => this.handleStressTestStart(data));
        this.ws.on('stress_test_end', (data) => this.handleStressTestEnd(data));
        this.ws.on('stats', (data) => this.handleStats(data));
        this.ws.on('performance', (data) => this.handlePerformance(data));
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
        
        // Stress test button
        document.getElementById('stressTestBtn').addEventListener('click', () => {
            this.runStressTest();
        });
    }

    setupUI() {
        // Initialize with mock data for testing
        this.generateMockData();

        // Initialize modern order entry state
        this.currentSide = 'buy';
        this.currentType = 'limit';

        // Setup input listeners for total calculation
        document.getElementById('orderPrice').addEventListener('input', () => this.updateOrderTotal());
        document.getElementById('orderQty').addEventListener('input', () => this.updateOrderTotal());
    }

    // Modern UI functions
    setSide(side) {
        this.currentSide = side;
        document.getElementById('orderSide').value = side;

        // Update tab styles
        document.querySelectorAll('.side-tab').forEach(tab => tab.classList.remove('active'));
        document.getElementById(side === 'buy' ? 'buyTab' : 'sellTab').classList.add('active');

        // Update submit button
        const submitBtn = document.getElementById('submitOrder');
        submitBtn.className = `submit-order-btn ${side}`;
        submitBtn.querySelector('.btn-text').textContent =
            `Place ${side.charAt(0).toUpperCase() + side.slice(1)} Order`;
    }

    setType(type) {
        this.currentType = type;
        document.getElementById('orderType').value = type;

        // Update toggle styles
        document.querySelectorAll('.type-toggle').forEach(btn => btn.classList.remove('active'));
        document.getElementById(type === 'limit' ? 'limitBtn' : 'marketBtn').classList.add('active');

        // Handle price input visibility
        const priceSection = document.getElementById('priceSection');
        const priceInput = document.getElementById('orderPrice');
        if (type === 'market') {
            priceSection.style.display = 'none';
            priceInput.value = '';
        } else {
            priceSection.style.display = 'block';
        }

        this.updateOrderTotal();
    }

    setQuantity(qty) {
        document.getElementById('orderQty').value = qty;
        this.updateOrderTotal();
    }

    updateOrderTotal() {
        const price = parseFloat(document.getElementById('orderPrice').value) || 0;
        const qty = parseFloat(document.getElementById('orderQty').value) || 0;
        const total = price * qty;
        const totalEl = document.getElementById('orderTotal');
        if (totalEl) {
            totalEl.textContent = `${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
        }
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
        
        // Update analytics
        if (this.analytics) {
            this.analytics.updateOrderBook(data);
        }

        // Update metrics
        const bbo = this.getBBO(data.bids, data.asks);
        if (bbo) {
            document.getElementById('midPrice').textContent =
                ((bbo.bidPrice + bbo.askPrice) / 2).toFixed(0);

            const imbalance = ((bbo.bidQty - bbo.askQty) / (bbo.bidQty + bbo.askQty)) * 100;
            document.getElementById('imbalance').textContent = imbalance.toFixed(1) + '%';
        }
    }

    handleOrderSubmitted(data) {
        // Add order to manual orders list immediately
        const order = {
            side: data.side,
            type: data.orderType,
            price: data.price,
            quantity: data.quantity,
            timestamp: data.timestamp || Date.now(),
            manual: true,
            status: data.status || 'pending',
            orderId: data.order_id
        };
        
        this.manualTrades.unshift(order);
        if (this.manualTrades.length > this.maxManualTrades) {
            this.manualTrades.pop();
        }
        this.renderManualTrades();
    }
    
    handleTrade(data) {
        // Mark if this is a manual trade (has manual flag)
        const isManual = data.manual === true;
        
        // Update analytics
        if (this.analytics) {
            this.analytics.updateTrade(data);
        }
        
        // Add to all trades
        this.trades.unshift(data);
        if (this.trades.length > this.maxTrades) {
            this.trades.pop();
        }
        
        // If manual trade, update corresponding order status to 'filled'
        if (isManual) {
            // Find and update the order in manual trades
            const orderIndex = this.manualTrades.findIndex(o => 
                o.side === data.side && 
                Math.abs(o.price - data.price) < 1 && 
                o.status === 'pending'
            );
            if (orderIndex !== -1) {
                this.manualTrades[orderIndex].status = 'filled';
            } else {
                // Add as new trade if not found
                const tradeOrder = {
                    side: data.side,
                    type: 'limit',
                    price: data.price,
                    quantity: data.quantity,
                    timestamp: data.timestamp || Date.now(),
                    manual: true,
                    status: 'filled'
                };
                this.manualTrades.unshift(tradeOrder);
                if (this.manualTrades.length > this.maxManualTrades) {
                    this.manualTrades.pop();
                }
            }
            this.renderManualTrades();
        }

        // Render immediately for instant feedback
        this.renderTrades();
        this.updateTradeMetrics(data);
        
        // Add visual highlight for new trades
        if (this.tradesList.firstChild) {
            this.tradesList.firstChild.classList.add('trade-new');
            setTimeout(() => {
                if (this.tradesList.firstChild) {
                    this.tradesList.firstChild.classList.remove('trade-new');
                }
            }, 500);
        }
    }
    
    showTradeTab(tab) {
        this.currentTradeTab = tab;
        
        // Update tab buttons
        document.getElementById('allTradesTab').classList.toggle('active', tab === 'all');
        document.getElementById('manualTradesTab').classList.toggle('active', tab === 'manual');
        
        // Re-render trades (chart should NOT be affected)
        this.renderTrades();
        
        // Ensure chart maintains its size and data (fix for chart getting messed up)
        setTimeout(() => {
            if (this.chart && this.chart.canvas) {
                this.chart.resize();
            }
        }, 100);
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
    
    handlePerformance(data) {
        console.log('Performance data received:', data); // Debug log
        
        // Always update all fields, even if value is 0
        const opsEl = document.getElementById('ordersPerSecond');
        if (opsEl) {
            opsEl.textContent = this.formatLargeNumber(data.orders_per_second || 0);
            opsEl.className = 'perf-value';
            if (data.orders_per_second > 1000) {
                opsEl.classList.add('high-throughput');
            } else {
                opsEl.classList.remove('high-throughput');
            }
        }
        
        const tpsEl = document.getElementById('tradesPerSecond');
        if (tpsEl) {
            tpsEl.textContent = this.formatLargeNumber(data.trades_per_second || 0);
            tpsEl.className = 'perf-value';
            if (data.trades_per_second > 500) {
                tpsEl.classList.add('high-throughput');
            } else {
                tpsEl.classList.remove('high-throughput');
            }
        }
        
        const latencyEl = document.getElementById('avgLatency');
        if (latencyEl) {
            latencyEl.textContent = this.formatLargeNumber(data.avg_latency_us || 0);
        }
        
        const peakOpsEl = document.getElementById('peakOrdersPerSecond');
        if (peakOpsEl) {
            peakOpsEl.textContent = this.formatLargeNumber(data.peak_orders_per_second || 0);
        }
        
        const peakTpsEl = document.getElementById('peakTradesPerSecond');
        if (peakTpsEl) {
            peakTpsEl.textContent = this.formatLargeNumber(data.peak_trades_per_second || 0);
        }
        
        const totalOrdersEl = document.getElementById('totalOrdersProcessed');
        if (totalOrdersEl) {
            totalOrdersEl.textContent = this.formatLargeNumber(data.total_orders || 0);
        }
        
        const uptimeEl = document.getElementById('uptime');
        if (uptimeEl && data.uptime_seconds !== undefined) {
            const uptime = data.uptime_seconds;
            const hours = Math.floor(uptime / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            const seconds = Math.floor(uptime % 60);
            let uptimeStr = '';
            if (hours > 0) uptimeStr += `${hours}h `;
            if (minutes > 0) uptimeStr += `${minutes}m `;
            uptimeStr += `${seconds}s`;
            uptimeEl.textContent = uptimeStr;
        }
    }
    
    formatLargeNumber(num) {
        if (num === undefined || num === null || isNaN(num)) {
            return '0';
        }
        if (num >= 1000000) {
            return (num / 1000000).toFixed(2) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toFixed(2);
    }
    
    runStressTest() {
        const numOrders = parseInt(document.getElementById('stressNumOrders').value) || 10000;
        const side = document.getElementById('stressSide').value;
        
        if (numOrders < 100) {
            alert('Minimum 100 orders required');
            return;
        }
        
        if (numOrders > 10000000) {
            if (!confirm(`EXTREME MODE: You are about to generate ${numOrders.toLocaleString()} orders at 10M+ orders/sec. This will be INTENSE. Continue?`)) {
                return;
            }
        }
        
        const btn = document.getElementById('stressTestBtn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⚡ RUNNING...';
        btn.classList.add('stress-active');
        
        // Add visual indicator
        document.body.classList.add('stress-test-active');
        
        // Send stress test request
        this.ws.send(JSON.stringify({
            type: 'stress_test',
            num_orders: numOrders,
            side: side,
            orderType: 'limit',
            base_price: 10000,
            price_range: 100,
            qty_range: [10, 1000]
        }));
        
        // Re-enable button after completion (server will send result)
        this.stressTestRunning = true;
    }
    
    handleStressTestStart(data) {
        // Visual feedback when stress test starts
        document.body.classList.add('stress-test-active');
        console.log(`[STRESS TEST] Starting: ${data.num_orders} orders`);
    }
    
    handleStressTestEnd(data) {
        // Visual feedback when stress test ends
        document.body.classList.remove('stress-test-active');
        const btn = document.getElementById('stressTestBtn');
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Run Stress Test';
            btn.classList.remove('stress-active');
        }
        this.stressTestRunning = false;
        console.log(`[STRESS TEST] Completed: ${data.orders_per_second.toLocaleString()} orders/sec`);
    }

    renderTrades() {
        this.tradesList.innerHTML = '';

        // Filter trades based on current tab
        const tradesToShow = this.currentTradeTab === 'manual' 
            ? this.trades.filter(t => t.manual === true)
            : this.trades;

        if (tradesToShow.length === 0) {
            this.tradesList.innerHTML = '<div class="empty-state">No trades to display</div>';
            return;
        }

        tradesToShow.forEach(trade => {
            const div = document.createElement('div');
            div.className = `trade-item ${trade.side} ${trade.manual ? 'manual-trade' : ''}`;

            // Convert timestamp to IST market hours (9:30 AM to 3:30 PM)
            const timeStr = this.formatISTTime(trade.timestamp);

            div.innerHTML = `
                <div class="trade-price">${this.formatPrice(trade.price)}</div>
                <div class="trade-qty">${this.formatQty(trade.quantity)}</div>
                <div class="trade-time">${timeStr}</div>
                ${trade.manual ? '<div class="trade-badge manual">Manual</div>' : ''}
            `;

            this.tradesList.appendChild(div);
        });
    }
    
    renderManualTrades() {
        this.manualTradesList.innerHTML = '';
        
        if (this.manualTrades.length === 0) {
            this.manualTradesList.innerHTML = '<div class="empty-state">No orders placed yet</div>';
            const countEl = document.getElementById('manualCount');
            if (countEl) countEl.textContent = '0';
            return;
        }

        // Show last 20 orders
        const ordersToShow = this.manualTrades.slice(0, 20);

        ordersToShow.forEach(order => {
            const div = document.createElement('div');
            div.className = `manual-trade-item ${order.side}`;

            const timeStr = this.formatISTTime(order.timestamp);
            const statusBadge = order.status === 'filled' ? '<span class="status-badge filled">✓</span>' : 
                              order.status === 'pending' ? '<span class="status-badge pending">⏳</span>' : '';

            div.innerHTML = `
                <div class="manual-trade-header">
                    <span class="manual-trade-side ${order.side}">${order.side.toUpperCase()}</span>
                    <span class="manual-trade-time">${timeStr}</span>
                </div>
                <div class="manual-trade-details">
                    <div class="manual-trade-price">₹${this.formatPrice(order.price || 0)}</div>
                    <div class="manual-trade-qty">${this.formatQty(order.quantity)}</div>
                    ${statusBadge}
                </div>
            `;

            this.manualTradesList.appendChild(div);
        });
        
        // Update manual order count
        this.manualOrderCount = this.manualTrades.length;
        const countEl = document.getElementById('manualCount');
        if (countEl) {
            countEl.textContent = this.manualOrderCount;
        }
    }
    
    formatISTTime(timestamp) {
        // Use a progressive time based on order count to show live movement
        // Market hours: 9:30 AM to 3:30 PM IST (6 hours = 360 minutes)
        const marketStartMinutes = 9 * 60 + 30; // 9:30 AM = 570 minutes
        const marketEndMinutes = 15 * 60 + 30; // 3:30 PM = 930 minutes
        const marketDuration = marketEndMinutes - marketStartMinutes; // 360 minutes
        
        // Use total orders as a counter to progress through market hours
        // This ensures time moves forward as more orders come in
        const orderIndex = this.trades.length + this.manualTrades.length;
        
        // Progress through market hours based on order count
        // Each order advances time by ~1 minute (for demo purposes)
        const minutesIntoMarket = (orderIndex * 1) % marketDuration;
        const totalMinutes = marketStartMinutes + minutesIntoMarket;
        
        let hours = Math.floor(totalMinutes / 60);
        let minutes = totalMinutes % 60;
        
        // Ensure within market hours
        if (hours < 9 || (hours === 9 && minutes < 30)) {
            hours = 9;
            minutes = 30;
        } else if (hours > 15 || (hours === 15 && minutes > 30)) {
            hours = 15;
            minutes = 30;
        }
        
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const displayHours = hours > 12 ? hours - 12 : (hours === 0 ? 12 : hours);
        const displayMinutes = minutes.toString().padStart(2, '0');
        
        return `${displayHours}:${displayMinutes} ${ampm}`;
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
            // Immediately add to manual orders list (even before trade confirmation)
            const manualOrder = {
                side: side,
                type: type,
                price: price,
                quantity: qty,
                timestamp: Date.now(),
                manual: true,
                status: 'pending'
            };
            
            this.manualTrades.unshift(manualOrder);
            if (this.manualTrades.length > this.maxManualTrades) {
                this.manualTrades.pop();
            }
            this.renderManualTrades();
            
            // Show success animation
            const btn = document.getElementById('submitOrder');
            const originalText = btn.innerHTML;
            btn.textContent = '✓ Submitted';
            btn.classList.add('success');

            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.remove('success');
            }, 1000);
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
