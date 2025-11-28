// Market Analytics
class MarketAnalytics {
    constructor() {
        // Market data tracking
        this.tradeHistory = [];
        this.priceHistory = [];
        this.spreadHistory = [];
        this.orderBookSnapshots = [];
        this.vwapData = { totalVolume: 0, totalValue: 0 };
    }

    updateTrade(tradeData) {
        // Store trade for VWAP calculation
        this.tradeHistory.push({
            price: tradeData.price,
            quantity: tradeData.quantity,
            timestamp: tradeData.timestamp || Date.now(),
            side: tradeData.side || null
        });

        // Keep only last 1000 trades
        if (this.tradeHistory.length > 1000) {
            this.tradeHistory.shift();
        }

        // Update VWAP
        this.vwapData.totalVolume += tradeData.quantity;
        this.vwapData.totalValue += tradeData.price * tradeData.quantity;

        // Update price history
        this.priceHistory.push(tradeData.price);
        if (this.priceHistory.length > 100) {
            this.priceHistory.shift();
        }

        this.updateInsights();
    }

    updateOrderBook(l2Data) {
        this.orderBookSnapshots.push({
            bids: l2Data.bids || [],
            asks: l2Data.asks || [],
            timestamp: Date.now()
        });

        // Keep only last 50 snapshots
        if (this.orderBookSnapshots.length > 50) {
            this.orderBookSnapshots.shift();
        }

        // Calculate spread
        if (l2Data.bids && l2Data.bids.length > 0 && l2Data.asks && l2Data.asks.length > 0) {
            const spread = l2Data.asks[0].price - l2Data.bids[0].price;
            this.spreadHistory.push(spread);
            if (this.spreadHistory.length > 100) {
                this.spreadHistory.shift();
            }
        }

        this.updateInsights();
    }

    updateInsights() {
        this.updateOrderFlowImbalance();
        this.updateLiquidityScore();
        this.updateVWAP();
        this.updateSpreadVolatility();
        this.updateDepthConcentration();
        this.updateMarketPressure();
        this.updateOrderBookDepth();
        this.updatePriceImpact();
        this.updateTradeVelocity();
        this.updateRelativeSpread();
        this.updateAvgOrderSize();
        this.updateMarketEfficiency();
        this.updatePriceMomentum();
        this.updateVolumeRatio();
        this.updateEffectiveSpread();
    }

    updateOrderFlowImbalance() {
        if (this.orderBookSnapshots.length === 0) return;

        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        if (!latest.bids || !latest.asks || latest.bids.length === 0 || latest.asks.length === 0) return;

        const bidQty = latest.bids[0].qty;
        const askQty = latest.asks[0].qty;
        const totalQty = bidQty + askQty;

        if (totalQty === 0) return;

        const imbalance = ((bidQty - askQty) / totalQty) * 100;
        const imbalanceEl = document.getElementById('orderFlowImbalance');
        const imbalanceBar = document.getElementById('imbalanceBar');
        const imbalanceDetail = document.getElementById('imbalanceDetail');

        if (imbalanceEl) {
            const sign = imbalance >= 0 ? '+' : '';
            imbalanceEl.textContent = `${sign}${imbalance.toFixed(1)}%`;
            imbalanceEl.style.color = imbalance > 0 ? 'var(--bid-color)' : 
                                      imbalance < 0 ? 'var(--ask-color)' : 'var(--text-primary)';
        }

        if (imbalanceBar) {
            const normalized = Math.abs(imbalance);
            imbalanceBar.style.width = `${Math.min(normalized, 100)}%`;
            imbalanceBar.style.background = imbalance > 0 ? 
                'linear-gradient(90deg, var(--bid-color), #00d4ff)' :
                'linear-gradient(90deg, var(--ask-color), #ff3388)';
        }

        if (imbalanceDetail) {
            if (imbalance > 20) {
                imbalanceDetail.textContent = 'Strong Buy Pressure';
            } else if (imbalance > 5) {
                imbalanceDetail.textContent = 'Moderate Buy Pressure';
            } else if (imbalance < -20) {
                imbalanceDetail.textContent = 'Strong Sell Pressure';
            } else if (imbalance < -5) {
                imbalanceDetail.textContent = 'Moderate Sell Pressure';
            } else {
                imbalanceDetail.textContent = 'Neutral';
            }
        }
    }

    updateLiquidityScore() {
        if (this.orderBookSnapshots.length === 0) return;

        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        if (!latest.bids || !latest.asks) return;

        const topBidLiquidity = latest.bids.slice(0, 5).reduce((sum, level) => sum + level.qty, 0);
        const topAskLiquidity = latest.asks.slice(0, 5).reduce((sum, level) => sum + level.qty, 0);
        const totalLiquidity = topBidLiquidity + topAskLiquidity;

        const score = Math.min((totalLiquidity / 10000) * 100, 100);

        const scoreEl = document.getElementById('liquidityScore');
        const liquidityBar = document.getElementById('liquidityBar');
        const liquidityDetail = document.getElementById('liquidityDetail');

        if (scoreEl) {
            scoreEl.textContent = score.toFixed(0);
            scoreEl.style.color = score > 70 ? 'var(--success)' : 
                                 score > 40 ? 'var(--warning)' : 'var(--danger)';
        }

        if (liquidityBar) {
            liquidityBar.style.width = `${score}%`;
            liquidityBar.style.background = score > 70 ? 
                'linear-gradient(90deg, var(--success), #10b981)' :
                score > 40 ?
                'linear-gradient(90deg, var(--warning), #f59e0b)' :
                'linear-gradient(90deg, var(--danger), #ef4444)';
        }

        if (liquidityDetail) {
            if (score > 70) {
                liquidityDetail.textContent = 'Excellent';
            } else if (score > 40) {
                liquidityDetail.textContent = 'Moderate';
            } else {
                liquidityDetail.textContent = 'Low';
            }
        }
    }

    updateVWAP() {
        if (this.vwapData.totalVolume === 0) return;

        const vwap = this.vwapData.totalValue / this.vwapData.totalVolume;
        const vwapEl = document.getElementById('vwap');
        const vwapDetail = document.getElementById('vwapDetail');

        if (vwapEl) {
            vwapEl.textContent = this.formatPrice(vwap);
        }

        if (vwapDetail && this.priceHistory.length > 0) {
            const lastPrice = this.priceHistory[this.priceHistory.length - 1];
            const diff = ((lastPrice - vwap) / vwap) * 100;
            const sign = diff >= 0 ? '+' : '';
            vwapDetail.textContent = `${sign}${diff.toFixed(2)}% vs Last Price`;
        }
    }

    updateSpreadVolatility() {
        if (this.spreadHistory.length < 10) return;

        const mean = this.spreadHistory.reduce((a, b) => a + b, 0) / this.spreadHistory.length;
        const variance = this.spreadHistory.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / this.spreadHistory.length;
        const stdDev = Math.sqrt(variance);
        const volatility = (stdDev / mean) * 100;

        const volEl = document.getElementById('spreadVolatility');
        const volDetail = document.getElementById('spreadVolatilityDetail');

        if (volEl) {
            volEl.textContent = `${volatility.toFixed(1)}%`;
            volEl.style.color = volatility < 5 ? 'var(--success)' : 
                               volatility < 15 ? 'var(--warning)' : 'var(--danger)';
        }

        if (volDetail) {
            if (volatility < 5) {
                volDetail.textContent = 'Very Stable';
            } else if (volatility < 15) {
                volDetail.textContent = 'Moderately Stable';
            } else {
                volDetail.textContent = 'High Volatility';
            }
        }
    }

    updateDepthConcentration() {
        if (this.orderBookSnapshots.length === 0) return;

        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        if (!latest.bids || !latest.asks) return;

        const top3BidQty = latest.bids.slice(0, 3).reduce((sum, level) => sum + level.qty, 0);
        const top3AskQty = latest.asks.slice(0, 3).reduce((sum, level) => sum + level.qty, 0);
        const totalBidQty = latest.bids.reduce((sum, level) => sum + level.qty, 0);
        const totalAskQty = latest.asks.reduce((sum, level) => sum + level.qty, 0);

        const bidConcentration = totalBidQty > 0 ? (top3BidQty / totalBidQty) * 100 : 0;
        const askConcentration = totalAskQty > 0 ? (top3AskQty / totalAskQty) * 100 : 0;
        const avgConcentration = (bidConcentration + askConcentration) / 2;

        const concEl = document.getElementById('depthConcentration');
        const concDetail = document.getElementById('depthConcentrationDetail');

        if (concEl) {
            concEl.textContent = `${avgConcentration.toFixed(0)}%`;
        }

        if (concDetail) {
            if (avgConcentration > 70) {
                concDetail.textContent = 'Highly Concentrated';
            } else if (avgConcentration > 40) {
                concDetail.textContent = 'Moderately Distributed';
            } else {
                concDetail.textContent = 'Well Distributed';
            }
        }
    }

    updateMarketPressure() {
        if (this.tradeHistory.length < 5) return;

        const recentTrades = this.tradeHistory.slice(-30);
        let buyVolume = 0;
        let sellVolume = 0;

        recentTrades.forEach(trade => {
            if (trade.side === 'buy') {
                buyVolume += trade.quantity;
            } else if (trade.side === 'sell') {
                sellVolume += trade.quantity;
            } else {
                const tradeIndex = this.tradeHistory.indexOf(trade);
                if (tradeIndex > 0 && this.priceHistory.length > tradeIndex) {
                    const prevPrice = this.priceHistory[tradeIndex - 1];
                    if (trade.price >= prevPrice) {
                        buyVolume += trade.quantity;
                    } else {
                        sellVolume += trade.quantity;
                    }
                }
            }
        });

        const totalVolume = buyVolume + sellVolume;
        if (totalVolume === 0) return;

        const pressure = ((buyVolume - sellVolume) / totalVolume) * 100;

        const pressureEl = document.getElementById('marketPressure');
        const pressureBar = document.getElementById('pressureBar');
        const pressureDetail = document.getElementById('pressureDetail');

        if (pressureEl) {
            const sign = pressure >= 0 ? '+' : '';
            pressureEl.textContent = `${sign}${pressure.toFixed(1)}%`;
            pressureEl.style.color = pressure > 0 ? 'var(--bid-color)' : 'var(--ask-color)';
        }

        if (pressureBar) {
            const normalized = Math.abs(pressure);
            pressureBar.style.width = `${Math.min(normalized, 100)}%`;
            pressureBar.style.background = pressure > 0 ?
                'linear-gradient(90deg, var(--bid-color), #00d4ff)' :
                'linear-gradient(90deg, var(--ask-color), #ff3388)';
        }

        if (pressureDetail) {
            if (pressure > 30) {
                pressureDetail.textContent = 'Strong Buy Pressure';
            } else if (pressure > 10) {
                pressureDetail.textContent = 'Buy Pressure';
            } else if (pressure < -30) {
                pressureDetail.textContent = 'Strong Sell Pressure';
            } else if (pressure < -10) {
                pressureDetail.textContent = 'Sell Pressure';
            } else {
                pressureDetail.textContent = 'Balanced';
            }
        }
    }

    updateOrderBookDepth() {
        if (this.orderBookSnapshots.length === 0) return;

        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        if (!latest.bids || !latest.asks) return;

        const totalBidDepth = latest.bids.reduce((sum, level) => sum + level.qty, 0);
        const totalAskDepth = latest.asks.reduce((sum, level) => sum + level.qty, 0);
        const totalDepth = totalBidDepth + totalAskDepth;

        const depthEl = document.getElementById('orderBookDepth');
        const depthDetail = document.getElementById('orderBookDepthDetail');

        if (depthEl) {
            depthEl.textContent = this.formatQty(totalDepth);
        }

        if (depthDetail) {
            depthDetail.textContent = `Bid: ${this.formatQty(totalBidDepth)} | Ask: ${this.formatQty(totalAskDepth)}`;
        }
    }

    updatePriceImpact() {
        if (this.tradeHistory.length < 10) return;

        // Calculate average price change per unit volume
        const recentTrades = this.tradeHistory.slice(-50);
        let totalPriceChange = 0;
        let totalVolume = 0;

        for (let i = 1; i < recentTrades.length; i++) {
            const priceChange = Math.abs(recentTrades[i].price - recentTrades[i-1].price);
            const volume = recentTrades[i].quantity;
            totalPriceChange += priceChange * volume;
            totalVolume += volume;
        }

        if (totalVolume === 0) return;

        const avgPrice = recentTrades.reduce((sum, t) => sum + t.price, 0) / recentTrades.length;
        const priceImpact = (totalPriceChange / totalVolume) / avgPrice * 10000; // Basis points

        const impactEl = document.getElementById('priceImpact');
        const impactDetail = document.getElementById('priceImpactDetail');

        if (impactEl) {
            impactEl.textContent = `${priceImpact.toFixed(2)} bps`;
            impactEl.style.color = priceImpact < 5 ? 'var(--success)' : 
                                 priceImpact < 15 ? 'var(--warning)' : 'var(--danger)';
        }

        if (impactDetail) {
            if (priceImpact < 5) {
                impactDetail.textContent = 'Low impact - liquid';
            } else if (priceImpact < 15) {
                impactDetail.textContent = 'Moderate impact';
            } else {
                impactDetail.textContent = 'High impact - illiquid';
            }
        }
    }

    updateTradeVelocity() {
        if (this.tradeHistory.length < 2) return;

        // Calculate trades per minute based on recent activity
        const recentTrades = this.tradeHistory.slice(-100);
        if (recentTrades.length < 2) return;

        const timeSpan = (recentTrades[0].timestamp - recentTrades[recentTrades.length - 1].timestamp) / 1000; // seconds
        const tradesPerMinute = timeSpan > 0 ? (recentTrades.length / timeSpan) * 60 : 0;

        const velocityEl = document.getElementById('tradeVelocity');
        const velocityDetail = document.getElementById('tradeVelocityDetail');

        if (velocityEl) {
            velocityEl.textContent = `${tradesPerMinute.toFixed(1)}`;
        }

        if (velocityDetail) {
            if (tradesPerMinute > 10) {
                velocityDetail.textContent = 'High activity';
            } else if (tradesPerMinute > 2) {
                velocityDetail.textContent = 'Moderate activity';
            } else {
                velocityDetail.textContent = 'Low activity';
            }
        }
    }

    updateRelativeSpread() {
        if (this.orderBookSnapshots.length === 0) return;

        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        if (!latest.bids || !latest.asks || latest.bids.length === 0 || latest.asks.length === 0) return;

        const bidPrice = latest.bids[0].price;
        const askPrice = latest.asks[0].price;
        const midPrice = (bidPrice + askPrice) / 2;
        const spread = askPrice - bidPrice;
        const relativeSpread = (spread / midPrice) * 100;

        const spreadEl = document.getElementById('relativeSpread');
        const spreadDetail = document.getElementById('relativeSpreadDetail');

        if (spreadEl) {
            spreadEl.textContent = `${relativeSpread.toFixed(3)}%`;
            spreadEl.style.color = relativeSpread < 0.1 ? 'var(--success)' : 
                                 relativeSpread < 0.5 ? 'var(--warning)' : 'var(--danger)';
        }

        if (spreadDetail) {
            if (relativeSpread < 0.1) {
                spreadDetail.textContent = 'Very tight';
            } else if (relativeSpread < 0.5) {
                spreadDetail.textContent = 'Tight';
            } else {
                spreadDetail.textContent = 'Wide';
            }
        }
    }

    updateAvgOrderSize() {
        if (this.orderBookSnapshots.length === 0) return;

        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        if (!latest.bids || !latest.asks) return;

        // Calculate average order size (quantity per order)
        const allLevels = [...latest.bids, ...latest.asks];
        let totalQty = 0;
        let totalOrders = 0;

        allLevels.forEach(level => {
            totalQty += level.qty;
            totalOrders += level.orders || 1;
        });

        const avgSize = totalOrders > 0 ? totalQty / totalOrders : 0;

        const sizeEl = document.getElementById('avgOrderSize');
        const sizeDetail = document.getElementById('avgOrderSizeDetail');

        if (sizeEl) {
            sizeEl.textContent = this.formatQty(avgSize);
        }

        if (sizeDetail) {
            if (avgSize > 500) {
                sizeDetail.textContent = 'Large orders';
            } else if (avgSize > 100) {
                sizeDetail.textContent = 'Medium orders';
            } else {
                sizeDetail.textContent = 'Small orders';
            }
        }
    }

    updateMarketEfficiency() {
        if (this.orderBookSnapshots.length === 0) return;

        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        if (!latest.bids || !latest.asks || latest.bids.length === 0 || latest.asks.length === 0) return;

        // Market efficiency = tightness (inverse of spread) + depth
        const bidPrice = latest.bids[0].price;
        const askPrice = latest.asks[0].price;
        const midPrice = (bidPrice + askPrice) / 2;
        const spread = askPrice - bidPrice;
        const relativeSpread = (spread / midPrice) * 100;

        const top5BidDepth = latest.bids.slice(0, 5).reduce((sum, level) => sum + level.qty, 0);
        const top5AskDepth = latest.asks.slice(0, 5).reduce((sum, level) => sum + level.qty, 0);
        const avgDepth = (top5BidDepth + top5AskDepth) / 2;

        // Efficiency score: tight spread (low is good) + high depth (high is good)
        const tightnessScore = Math.max(0, 100 - (relativeSpread * 200)); // Lower spread = higher score
        const depthScore = Math.min(100, (avgDepth / 5000) * 100); // Normalize depth
        const efficiency = (tightnessScore * 0.6 + depthScore * 0.4); // Weighted combination

        const effEl = document.getElementById('marketEfficiency');
        const effBar = document.getElementById('efficiencyBar');
        const effDetail = document.getElementById('marketEfficiencyDetail');

        if (effEl) {
            effEl.textContent = `${efficiency.toFixed(0)}`;
            effEl.style.color = efficiency > 70 ? 'var(--success)' : 
                              efficiency > 40 ? 'var(--warning)' : 'var(--danger)';
        }

        if (effBar) {
            effBar.style.width = `${efficiency}%`;
            effBar.style.background = efficiency > 70 ? 
                'linear-gradient(90deg, var(--success), #10b981)' :
                efficiency > 40 ?
                'linear-gradient(90deg, var(--warning), #f59e0b)' :
                'linear-gradient(90deg, var(--danger), #ef4444)';
        }

        if (effDetail) {
            if (efficiency > 70) {
                effDetail.textContent = 'Highly efficient';
            } else if (efficiency > 40) {
                effDetail.textContent = 'Moderately efficient';
            } else {
                effDetail.textContent = 'Inefficient';
            }
        }
    }

    updatePriceMomentum() {
        if (this.priceHistory.length < 10) return;

        // Calculate short-term momentum (price change over recent trades)
        const recentPrices = this.priceHistory.slice(-20);
        const firstPrice = recentPrices[0];
        const lastPrice = recentPrices[recentPrices.length - 1];
        const momentum = ((lastPrice - firstPrice) / firstPrice) * 100;

        const momEl = document.getElementById('priceMomentum');
        const momDetail = document.getElementById('priceMomentumDetail');

        if (momEl) {
            const sign = momentum >= 0 ? '+' : '';
            momEl.textContent = `${sign}${momentum.toFixed(2)}%`;
            momEl.style.color = momentum > 0.5 ? 'var(--bid-color)' : 
                              momentum < -0.5 ? 'var(--ask-color)' : 'var(--text-primary)';
        }

        if (momDetail) {
            if (momentum > 1) {
                momDetail.textContent = 'Strong upward';
            } else if (momentum > 0.5) {
                momDetail.textContent = 'Moderate upward';
            } else if (momentum < -1) {
                momDetail.textContent = 'Strong downward';
            } else if (momentum < -0.5) {
                momDetail.textContent = 'Moderate downward';
            } else {
                momDetail.textContent = 'Neutral';
            }
        }
    }

    updateVolumeRatio() {
        if (this.tradeHistory.length < 10) return;

        // Calculate buy vs sell volume ratio
        const recentTrades = this.tradeHistory.slice(-50);
        let buyVolume = 0;
        let sellVolume = 0;

        recentTrades.forEach(trade => {
            if (trade.side === 'buy') {
                buyVolume += trade.quantity;
            } else if (trade.side === 'sell') {
                sellVolume += trade.quantity;
            }
        });

        const totalVolume = buyVolume + sellVolume;
        if (totalVolume === 0) return;

        const ratio = buyVolume / totalVolume; // 0 = all sell, 1 = all buy, 0.5 = balanced

        const ratioEl = document.getElementById('volumeRatio');
        const ratioBar = document.getElementById('volumeRatioBar');
        const ratioDetail = document.getElementById('volumeRatioDetail');

        if (ratioEl) {
            ratioEl.textContent = `${(ratio * 100).toFixed(1)}%`;
            ratioEl.style.color = ratio > 0.6 ? 'var(--bid-color)' : 
                                 ratio < 0.4 ? 'var(--ask-color)' : 'var(--text-primary)';
        }

        if (ratioBar) {
            ratioBar.style.width = `${ratio * 100}%`;
            ratioBar.style.background = ratio > 0.5 ?
                'linear-gradient(90deg, var(--bid-color), #00d4ff)' :
                'linear-gradient(90deg, var(--ask-color), #ff3388)';
        }

        if (ratioDetail) {
            if (ratio > 0.7) {
                ratioDetail.textContent = 'Heavy buy volume';
            } else if (ratio > 0.6) {
                ratioDetail.textContent = 'Buy volume dominant';
            } else if (ratio < 0.3) {
                ratioDetail.textContent = 'Heavy sell volume';
            } else if (ratio < 0.4) {
                ratioDetail.textContent = 'Sell volume dominant';
            } else {
                ratioDetail.textContent = 'Balanced volume';
            }
        }
    }

    formatPrice(price) {
        return price.toLocaleString('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    updateEffectiveSpread() {
        if (this.tradeHistory.length < 5 || this.orderBookSnapshots.length === 0) return;

        // Calculate effective spread: average deviation of trade prices from mid price
        const recentTrades = this.tradeHistory.slice(-30);
        const latest = this.orderBookSnapshots[this.orderBookSnapshots.length - 1];
        
        if (!latest.bids || !latest.asks || latest.bids.length === 0 || latest.asks.length === 0) return;

        const bidPrice = latest.bids[0].price;
        const askPrice = latest.asks[0].price;
        const midPrice = (bidPrice + askPrice) / 2;

        let totalDeviation = 0;
        let validTrades = 0;

        recentTrades.forEach(trade => {
            const deviation = Math.abs(trade.price - midPrice);
            totalDeviation += deviation;
            validTrades++;
        });

        if (validTrades === 0) return;

        const avgDeviation = totalDeviation / validTrades;
        const effectiveSpread = (avgDeviation / midPrice) * 100; // As percentage
        const quotedSpread = ((askPrice - bidPrice) / midPrice) * 100;

        const spreadEl = document.getElementById('effectiveSpread');
        const spreadDetail = document.getElementById('effectiveSpreadDetail');

        if (spreadEl) {
            spreadEl.textContent = `${effectiveSpread.toFixed(3)}%`;
            spreadEl.style.color = effectiveSpread < quotedSpread * 0.8 ? 'var(--success)' : 
                                 effectiveSpread < quotedSpread * 1.2 ? 'var(--warning)' : 'var(--danger)';
        }

        if (spreadDetail) {
            const ratio = effectiveSpread / quotedSpread;
            if (ratio < 0.8) {
                spreadDetail.textContent = 'Better than quoted';
            } else if (ratio < 1.2) {
                spreadDetail.textContent = 'Near quoted spread';
            } else {
                spreadDetail.textContent = 'Worse than quoted';
            }
        }
    }

    formatQty(qty) {
        if (qty >= 1000000) return (qty / 1000000).toFixed(2) + 'M';
        if (qty >= 1000) return (qty / 1000).toFixed(1) + 'K';
        return qty.toFixed(0);
    }
}

window.MarketAnalytics = MarketAnalytics;

