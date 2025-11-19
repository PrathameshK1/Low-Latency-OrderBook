#pragma once
#include "lob/core/Types.h"
#include <vector>

namespace lob {

/**
 * @brief Represents a single price level with aggregated quantity
 */
struct PriceLevel {
    Price price;
    Quantity totalQuantity;
    uint32_t orderCount;
    
    PriceLevel() : price(0), totalQuantity(0), orderCount(0) {}
    PriceLevel(Price p, Quantity q, uint32_t c) 
        : price(p), totalQuantity(q), orderCount(c) {}
};

/**
 * @brief Best Bid and Offer (BBO) snapshot
 */
struct BBO {
    Price bidPrice;
    Quantity bidQty;
    Price askPrice;
    Quantity askQty;
    Timestamp timestamp;
    
    BBO() : bidPrice(0), bidQty(0), askPrice(0), askQty(0), timestamp(0) {}
    
    // Market metrics
    Price spread() const { 
        return (askPrice > bidPrice) ? (askPrice - bidPrice) : 0; 
    }
    
    double midPrice() const { 
        return (bidPrice + askPrice) / 2.0; 
    }
    
    // Imbalance: +1 = all bids, -1 = all asks, 0 = balanced
    double imbalance() const {
        if (bidQty == 0 && askQty == 0) return 0.0;
        return static_cast<double>(bidQty - askQty) / (bidQty + askQty);
    }
    
    bool isValid() const {
        return bidPrice > 0 && askPrice > 0 && askPrice > bidPrice;
    }
};

/**
 * @brief Level 2 market data snapshot
 */
struct L2Snapshot {
    std::vector<PriceLevel> bids;  // Sorted descending by price
    std::vector<PriceLevel> asks;  // Sorted ascending by price
    Timestamp timestamp;
    uint64_t sequenceNumber;
    
    L2Snapshot() : timestamp(0), sequenceNumber(0) {}
    
    BBO getBBO() const {
        BBO bbo;
        bbo.timestamp = timestamp;
        
        if (!bids.empty()) {
            bbo.bidPrice = bids[0].price;
            bbo.bidQty = bids[0].totalQuantity;
        }
        
        if (!asks.empty()) {
            bbo.askPrice = asks[0].price;
            bbo.askQty = asks[0].totalQuantity;
        }
        
        return bbo;
    }
    
    // Calculate volume-weighted average price up to specified quantity
    double getVWAP(Side side, Quantity targetQty) const {
        const auto& levels = (side == Side::BUY) ? asks : bids;
        
        double totalValue = 0.0;
        Quantity totalQty = 0;
        
        for (const auto& level : levels) {
            Quantity qty = std::min(level.totalQuantity, targetQty - totalQty);
            totalValue += level.price * qty;
            totalQty += qty;
            
            if (totalQty >= targetQty) break;
        }
        
        return (totalQty > 0) ? (totalValue / totalQty) : 0.0;
    }
};

} // namespace lob
