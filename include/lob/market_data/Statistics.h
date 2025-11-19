#pragma once
#include "TradeListener.h"
#include <vector>
#include <mutex>
#include <atomic>
#include <deque>
#include <algorithm>

namespace lob {

/**
 * @brief Publishes trade and order events to registered listeners
 */
class TradePublisher {
private:
    std::vector<ITradeListener*> listeners;
    mutable std::mutex mutex;
    std::atomic<uint64_t> nextTradeId{1};

public:
    /**
     * @brief Register a listener for trade/order events
     */
    void subscribe(ITradeListener* listener) {
        std::lock_guard<std::mutex> lock(mutex);
        listeners.push_back(listener);
    }
    
    /**
     * @brief Unregister a listener
     */
    void unsubscribe(ITradeListener* listener) {
        std::lock_guard<std::mutex> lock(mutex);
        listeners.erase(
            std::remove(listeners.begin(), listeners.end(), listener),
            listeners.end()
        );
    }
    
    /**
     * @brief Publish a trade to all listeners
     */
    void publishTrade(Trade trade) {
        // Assign trade ID if not set
        if (trade.tradeId == 0) {
            trade.tradeId = nextTradeId.fetch_add(1);
        }
        
        std::lock_guard<std::mutex> lock(mutex);
        for (auto* listener : listeners) {
            if (listener) {
                listener->onTrade(trade);
            }
        }
    }
    
    /**
     * @brief Publish an order event to all listeners
     */
    void publishOrderEvent(const OrderEvent& event) {
        std::lock_guard<std::mutex> lock(mutex);
        for (auto* listener : listeners) {
            if (listener) {
                listener->onOrderEvent(event);
            }
        }
    }
    
    TradeId getNextTradeId() {
        return nextTradeId.fetch_add(1);
    }
};

/**
 * @brief Collects and maintains trading statistics
 */
class MarketStatistics : public ITradeListener {
private:
    std::atomic<uint64_t> totalTrades{0};
    std::atomic<uint64_t> totalVolume{0};
    std::atomic<Price> lastPrice{0};
    
    mutable std::mutex tradesMutex;
    std::deque<Trade> recentTrades;
    static constexpr size_t MAX_RECENT_TRADES = 1000;
    
public:
    void onTrade(const Trade& trade) override {
        totalTrades.fetch_add(1);
        totalVolume.fetch_add(trade.executionQuantity);
        lastPrice.store(trade.executionPrice);
        
        std::lock_guard<std::mutex> lock(tradesMutex);
        recentTrades.push_back(trade);
        if (recentTrades.size() > MAX_RECENT_TRADES) {
            recentTrades.pop_front();
        }
    }
    
    void onOrderEvent(const OrderEvent&) override {
        // Could track order statistics here
    }
    
    uint64_t getTotalTrades() const { return totalTrades.load(); }
    uint64_t getVolume() const { return totalVolume.load(); }
    Price getLastPrice() const { return lastPrice.load(); }
    
    /**
     * @brief Calculate VWAP from recent trades
     */
    double getVWAP(size_t numTrades = 100) const {
        std::lock_guard<std::mutex> lock(tradesMutex);
        
        if (recentTrades.empty()) return 0.0;
        
        double totalValue = 0.0;
        uint64_t totalQty = 0;
        
        size_t count = std::min(numTrades, recentTrades.size());
        auto it = recentTrades.rbegin();
        
        for (size_t i = 0; i < count; ++i, ++it) {
            totalValue += it->executionPrice * it->executionQuantity;
            totalQty += it->executionQuantity;
        }
        
        return (totalQty > 0) ? (totalValue / totalQty) : 0.0;
    }
    
    std::vector<Trade> getRecentTrades(size_t count = 10) const {
        std::lock_guard<std::mutex> lock(tradesMutex);
        
        std::vector<Trade> result;
        size_t n = std::min(count, recentTrades.size());
        
        auto it = recentTrades.rbegin();
        for (size_t i = 0; i < n; ++i, ++it) {
            result.push_back(*it);
        }
        
        return result;
    }
    
    void reset() {
        totalTrades.store(0);
        totalVolume.store(0);
        lastPrice.store(0);
        
        std::lock_guard<std::mutex> lock(tradesMutex);
        recentTrades.clear();
    }
};

} // namespace lob
