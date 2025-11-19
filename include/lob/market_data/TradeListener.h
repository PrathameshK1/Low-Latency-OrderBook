#pragma once
#include "lob/core/Types.h"
#include <string>

namespace lob {

/**
 * @brief Represents a trade execution
 */
struct Trade {
    TradeId tradeId;
    Timestamp timestamp;
    
    IdNumber buyOrderId;
    IdNumber sellOrderId;
    
    Price executionPrice;
    Quantity executionQuantity;
    
    Side aggressorSide;  // Which side initiated (took liquidity)
    
    Trade() : tradeId(0), timestamp(0), buyOrderId(0), sellOrderId(0),
              executionPrice(0), executionQuantity(0), aggressorSide(Side::BUY) {}
};

/**
 * @brief Order lifecycle events
 */
struct OrderEvent {
    enum class Type {
        ADDED,
        MODIFIED,
        CANCELED,
        FILLED,
        PARTIALLY_FILLED,
        REJECTED
    };
    
    Type type;
    OrderPointer order;
    Timestamp timestamp;
    std::string reason;  // For rejections
    
    OrderEvent() : type(Type::ADDED), timestamp(0) {}
    OrderEvent(Type t, OrderPointer o, Timestamp ts, const std::string& r = "")
        : type(t), order(o), timestamp(ts), reason(r) {}
};

/**
 * @brief Observer interface for trade and order events
 */
class ITradeListener {
public:
    virtual ~ITradeListener() = default;
    
    virtual void onTrade(const Trade& trade) = 0;
    virtual void onOrderEvent(const OrderEvent& event) = 0;
};

} // namespace lob
