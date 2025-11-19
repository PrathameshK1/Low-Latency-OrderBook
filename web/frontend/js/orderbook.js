// Order Book Visualization
class OrderBookVisualizer {
    constructor() {
        this.bidsLevels = document.getElementById('bidsLevels');
        this.asksLevels = document.getElementById('asksLevels');

        this.bestBidPrice = document.getElementById('bestBidPrice');
        this.bestBidQty = document.getElementById('bestBidQty');
        this.bestAskPrice = document.getElementById('bestAskPrice');
        this.bestAskQty = document.getElementById('bestAskQty');
        this.spreadValue = document.getElementById('spreadValue');

        this.maxDepth = 15;
        this.bids = [];
        this.asks = [];
    }

    updateL2Data(data) {
        this.bids = data.bids || [];
        this.asks = data.asks || [];

        this.renderOrderBook();
        this.updateBBO();
    }

    updateBBO() {
        if (this.bids.length > 0) {
            this.bestBidPrice.textContent = this.formatPrice(this.bids[0].price);
            this.bestBidQty.textContent = this.formatQty(this.bids[0].qty);
        } else {
            this.bestBidPrice.textContent = '-';
            this.bestBidQty.textContent = '-';
        }

        if (this.asks.length > 0) {
            this.bestAskPrice.textContent = this.formatPrice(this.asks[0].price);
            this.bestAskQty.textContent = this.formatQty(this.asks[0].qty);
        } else {
            this.bestAskPrice.textContent = '-';
            this.bestAskQty.textContent = '-';
        }

        // Calculate spread
        if (this.bids.length > 0 && this.asks.length > 0) {
            const spread = this.asks[0].price - this.bids[0].price;
            this.spreadValue.textContent = this.formatPrice(spread);
        } else {
            this.spreadValue.textContent = '-';
        }
    }

    renderOrderBook() {
        // Render bids (highest to lowest)
        this.bidsLevels.innerHTML = '';
        const maxBidQty = Math.max(...this.bids.slice(0, this.maxDepth).map(l => l.qty), 1);

        this.bids.slice(0, this.maxDepth).forEach(level => {
            const el = this.createLevelElement(level, 'bid', maxBidQty);
            this.bidsLevels.appendChild(el);
        });

        // Render asks (lowest to highest)
        this.asksLevels.innerHTML = '';
        const maxAskQty = Math.max(...this.asks.slice(0, this.maxDepth).map(l => l.qty), 1);

        this.asks.slice(0, this.maxDepth).forEach(level => {
            const el = this.createLevelElement(level, 'ask', maxAskQty);
            this.asksLevels.appendChild(el);
        });
    }

    createLevelElement(level, side, maxQty) {
        const div = document.createElement('div');
        div.className = `price-level ${side}`;

        // Calculate depth percentage for visualization
        const depthPercent = (level.qty / maxQty) * 100;
        div.style.setProperty('--depth-width', `${depthPercent}%`);

        div.innerHTML = `
            <span class="price">${this.formatPrice(level.price)}</span>
            <span class="qty">${this.formatQty(level.qty)}</span>
            <span class="count">${level.orders || 0}</span>
        `;

        return div;
    }

    formatPrice(price) {
        return price.toLocaleString('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    formatQty(qty) {
        if (qty >= 1000000) {
            return (qty / 1000000).toFixed(2) + 'M';
        } else if (qty >= 1000) {
            return (qty / 1000).toFixed(1) + 'K';
        }
        return qty.toLocaleString();
    }
}

window.OrderBookVisualizer = OrderBookVisualizer;
