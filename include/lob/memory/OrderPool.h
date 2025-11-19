#pragma once
#include "ObjectPool.h"
#include "lob/core/Order.h"

namespace lob {

/**
 * @brief Specialized memory pool for Order objects with factory methods
 */
class OrderPool {
private:
    ObjectPool<Order, 4096> pool;  // 4096 orders per block

public:
    OrderPool() = default;
    
    OrderPointer createOrder(IdNumber id, Side side, OrderType type, 
                            Price price, Quantity qty) {
        Order* rawPtr = pool.allocate(id, side, type, price, qty);
        return OrderPointer(rawPtr, PoolDeleter<Order>(&pool));
    }
    
    OrderPointer createLimitOrder(IdNumber id, Side side, Price price, Quantity qty) {
        return createOrder(id, side, OrderType::LIMIT, price, qty);
    }
    
    OrderPointer createMarketOrder(IdNumber id, Side side, Quantity qty) {
        Price price = (side == Side::BUY) ? MARKET_BUY_PRICE : MARKET_SELL_PRICE;
        return createOrder(id, side, OrderType::MARKET, price, qty);
    }
    
    size_t allocated() const { return pool.allocated(); }
    size_t capacity() const { return pool.capacity(); }
    size_t blockCount() const { return pool.blockCount(); }
    
    double utilization() const {
        size_t cap = capacity();
        return (cap > 0) ? (100.0 * allocated() / cap) : 0.0;
    }
};

} // namespace lob
