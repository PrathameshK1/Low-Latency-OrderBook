#pragma once
#include "lob/core/Order.h"
#include "lob/market_data/L2Data.h"
#include "lob/market_data/Statistics.h"
#include <list>
#include <map>
#include <unordered_map>
#include <chrono>

namespace lob {

/**
 * @brief Represents a price level containing all orders at a specific price
 */
struct PriceLevelData {
    Price price;
    std::list<OrderPointer> orders;  // Time-priority FIFO
    std::unordered_map<IdNumber, std::list<OrderPointer>::iterator> orderIters;  // For O(1) lookup
    
    PriceLevel getSnapshot() const {
        Quantity totalQty = 0;
        for (const auto& order : orders) {
            totalQty += order->getRemainingQuantity();
        }
        return PriceLevel(price, totalQty, static_cast<uint32_t>(orders.size()));
    }
};

using PriceLevelPointer = std::shared_ptr<PriceLevelData>;

/**
 * @brief High-performance limit order book with market data support
 * 
 * Features:
 * - Price-time priority matching
 * - O(1) order add/modify/cancel
 * - Market and limit orders
 * - L2 market data snapshots
 * - Trade event publishing
 */
class OrderBook {
private:
    // Bids: descending price (highest first)
    std::map<Price, PriceLevelPointer, std::greater<>> bids;
    
    // Asks: ascending price (lowest first)
    std::map<Price, PriceLevelPointer> asks;
    
    // Global order lookup
    std::unordered_map<IdNumber, OrderPointer> orders;
    
    // Trade publisher for event callbacks
    TradePublisher* publisher = nullptr;
    
    // Cached BBO for O(1) access
    mutable BBO cachedBBO;
    mutable bool bboDirty = true;
    mutable uint64_t sequenceNumber = 0;
    
    // Timestamp helper
    static Timestamp getCurrentTimestamp() {
        return std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::high_resolution_clock::now().time_since_epoch()
        ).count();
    }

public:
    OrderBook() = default;
    
    /**
     * @brief Set trade publisher for event callbacks
     */
    void setPublisher(TradePublisher* pub) {
        publisher = pub;
    }
    
    /**
     * @brief Add an order to the book and attempt matching
     * @param order The order to add
     */
    void addOrder(const OrderPointer& order);
    
    /**
     * @brief Modify an order (cancel + re-add)
     * @param idNumber Order ID to modify
     * @param newPrice New price
     * @param newQty New quantity
     * @return Modified order pointer
     */
    OrderPointer modifyOrder(IdNumber idNumber, Price newPrice, Quantity newQty);
    
    /**
     * @brief Cancel an order
     * @param idNumber Order ID to cancel
     */
    void cancelOrder(IdNumber idNumber);
    
    /**
     * @brief Match orders according to price-time priority
     */
    void matchOrders();
    
    /**
     * @brief Get order by ID
     */
    OrderPointer getOrderByID(IdNumber idNumber) const;
    
    /**
     * @brief Check if order exists
     */
    bool contains(IdNumber idNumber) const;
    
    /**
     * @brief Get total number of orders in book
     */
    std::size_t getNumberOfOrders() const { return orders.size(); }
    
    /**
     * @brief Get best bid and offer (cached, O(1))
     */
    BBO getBBO() const;
    
    /**
     * @brief Get L2 market data snapshot
     * @param depth Number of price levels per side
     */
    L2Snapshot getL2Snapshot(uint32_t depth = 10) const;

private:
    void addLimitOrder(const OrderPointer& order);
    void executeMarketOrder(const OrderPointer& order);
    void invalidateBBO() { bboDirty = true; }
    void publishOrderEvent(OrderEvent::Type type, const OrderPointer& order, 
                          const std::string& reason = "");
};

} // namespace lob
