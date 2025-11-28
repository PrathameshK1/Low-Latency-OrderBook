// Depth Chart Visualization using Canvas
class DepthChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.bids = [];
        this.asks = [];

        this.colors = {
            bid: 'rgba(0, 245, 255, 0.6)',
            ask: 'rgba(255, 0, 110, 0.6)',
            bidLine: '#00f5ff',
            askLine: '#ff006e',
            grid: 'rgba(255, 255, 255, 0.05)',
            text: '#a0aec0'
        };

        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        const rect = this.canvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) {
            // Canvas not visible yet, use default size
            this.width = 600;
            this.height = 400;
            return;
        }
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        this.width = rect.width;
        this.height = rect.height;
        this.draw();
    }

    updateData(bids, asks) {
        this.bids = bids || [];
        this.asks = asks || [];
        this.draw();
    }

    draw() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.width, this.height);

        if (this.bids.length === 0 && this.asks.length === 0) {
            this.drawNoData();
            return;
        }

        // Calculate cumulative depths
        const bidDepths = this.calculateCumulativeDepth(this.bids);
        const askDepths = this.calculateCumulativeDepth(this.asks);

        // Find price range
        const allPrices = [
            ...this.bids.map(b => b.price),
            ...this.asks.map(a => a.price)
        ];
        const minPrice = Math.min(...allPrices);
        const maxPrice = Math.max(...allPrices);
        const maxDepth = Math.max(
            bidDepths.length > 0 ? bidDepths[bidDepths.length - 1].cumQty : 0,
            askDepths.length > 0 ? askDepths[askDepths.length - 1].cumQty : 0
        );

        // Draw grid
        this.drawGrid(minPrice, maxPrice, maxDepth);

        // Draw depth curves
        this.drawDepthCurve(bidDepths, minPrice, maxPrice, maxDepth, 'bid');
        this.drawDepthCurve(askDepths, minPrice, maxPrice, maxDepth, 'ask');

        // Draw axes labels
        this.drawLabels(minPrice, maxPrice, maxDepth);
    }

    calculateCumulativeDepth(levels) {
        let cumQty = 0;
        return levels.map(level => {
            cumQty += level.qty;
            return { price: level.price, cumQty };
        });
    }

    drawGrid(minPrice, maxPrice, maxDepth) {
        const padding = 40;
        const chartWidth = this.width - 2 * padding;
        const chartHeight = this.height - 2 * padding;

        this.ctx.strokeStyle = this.colors.grid;
        this.ctx.lineWidth = 1;

        // Horizontal grid lines
        for (let i = 0; i <= 5; i++) {
            const y = padding + (chartHeight * i / 5);
            this.ctx.beginPath();
            this.ctx.moveTo(padding, y);
            this.ctx.lineTo(this.width - padding, y);
            this.ctx.stroke();
        }

        // Vertical grid lines
        for (let i = 0; i <= 5; i++) {
            const x = padding + (chartWidth * i / 5);
            this.ctx.beginPath();
            this.ctx.moveTo(x, padding);
            this.ctx.lineTo(x, this.height - padding);
            this.ctx.stroke();
        }
    }

    drawDepthCurve(depths, minPrice, maxPrice, maxDepth, type) {
        if (depths.length === 0) return;

        const padding = 40;
        const chartWidth = this.width - 2 * padding;
        const chartHeight = this.height - 2 * padding;

        const priceToX = (price) => {
            return padding + ((price - minPrice) / (maxPrice - minPrice)) * chartWidth;
        };

        const depthToY = (depth) => {
            return this.height - padding - (depth / maxDepth) * chartHeight;
        };

        // Fill area under curve
        this.ctx.fillStyle = this.colors[type];
        this.ctx.beginPath();
        this.ctx.moveTo(priceToX(depths[0].price), this.height - padding);

        depths.forEach(d => {
            this.ctx.lineTo(priceToX(d.price), depthToY(d.cumQty));
        });

        this.ctx.lineTo(priceToX(depths[depths.length - 1].price), this.height - padding);
        this.ctx.closePath();
        this.ctx.fill();

        // Draw line
        this.ctx.strokeStyle = this.colors[type + 'Line'];
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(priceToX(depths[0].price), depthToY(depths[0].cumQty));

        depths.forEach(d => {
            this.ctx.lineTo(priceToX(d.price), depthToY(d.cumQty));
        });

        this.ctx.stroke();
    }

    drawLabels(minPrice, maxPrice, maxDepth) {
        this.ctx.fillStyle = this.colors.text;
        this.ctx.font = '11px Inter';
        this.ctx.textAlign = 'center';

        const padding = 40;

        // Price labels (X-axis)
        for (let i = 0; i <= 5; i++) {
            const price = minPrice + ((maxPrice - minPrice) * i / 5);
            const x = padding + ((this.width - 2 * padding) * i / 5);
            this.ctx.fillText(price.toFixed(0), x, this.height - 20);
        }

        // Depth labels (Y-axis)
        this.ctx.textAlign = 'right';
        for (let i = 0; i <= 5; i++) {
            const depth = (maxDepth * i / 5);
            const y = this.height - padding - ((this.height - 2 * padding) * i / 5);
            this.ctx.fillText(this.formatQty(depth), padding - 10, y + 4);
        }
    }

    drawNoData() {
        this.ctx.fillStyle = this.colors.text;
        this.ctx.font = '16px Inter';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('Waiting for market data...', this.width / 2, this.height / 2);
    }

    formatQty(qty) {
        if (qty >= 1000000) return (qty / 1000000).toFixed(1) + 'M';
        if (qty >= 1000) return (qty / 1000).toFixed(1) + 'K';
        return qty.toFixed(0);
    }
}

window.DepthChart = DepthChart;
