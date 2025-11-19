#include "lob/core/OrderBook.h"
#include <stdexcept>
#include <string>
#include <cstdint>

namespace lob {

void OrderBook::addOrder(const OrderPointer& order) {
    if (order->isMarketOrder()) {
        executeMarketOrder(order);
    } else {
        addLimitOrder(order);
    }
}

void OrderBook::addLimitOrder(const OrderPointer& order) {
    PriceLevelPointer level;
    
    if (order->getSide() == Side::BUY) {
        // Get or create price level in bids
        if (!bids.contains(order->getPrice())) {
            auto newLevel = std::make_shared<PriceLevelData>();
            newLevel->price = order->getPrice();
            bids[order->getPrice()] = newLevel;
        }
        level = bids[order->getPrice()];
    } else {
        // Get or create price level in asks
        if (!asks.contains(order->getPrice())) {
            auto newLevel = std::make_shared<PriceLevelData>();
            newLevel->price = order->getPrice();
            asks[order->getPrice()] = newLevel;
        }
        level = asks[order->getPrice()];
    }
    
    // Add to end of list (time priority)
    auto it = level->orders.insert(level->orders.end(), order);
    level->orderIters[order->getIDNumber()] = it;
    
    // Add to global orders map
    orders[order->getIDNumber()] = order;
    
    invalidateBBO();
    publishOrderEvent(OrderEvent::Type::ADDED, order);
}

void OrderBook::executeMarketOrder(const OrderPointer& order) {
    Quantity remainingQty = order->getRemainingQuantity();
    Timestamp timestamp = getCurrentTimestamp();
    
    // Execute against opposite side
    while (remainingQty > 0) {
        PriceLevelPointer level;
        std::map<Price, PriceLevelPointer>::iterator it;
        
        // Get next level from opposite side
        if (order->getSide() == Side::BUY) {
            if (asks.empty()) break;
            it = asks.begin();
        } else {
            if (bids.empty()) break;
            it = bids.begin();
        }
        
        level = it->second;
        
        if (level->orders.empty()) {
            if (order->getSide() == Side::BUY) {
                asks.erase(it);
            } else {
                bids.erase(it);
            }
            continue;
        }
        
        OrderPointer passiveOrder = level->orders.front();
        Quantity matchQty = std::min(remainingQty, passiveOrder->getRemainingQuantity());
        
        // Execute trade
        order->fill(matchQty);
        passiveOrder->fill(matchQty);
        remainingQty -= matchQty;
        
        // Publish trade event
        if (publisher) {
            Trade trade;
            trade.timestamp = timestamp;
            trade.executionPrice = passiveOrder->getPrice();
            trade.executionQuantity = matchQty;
            trade.aggressorSide = order->getSide();
            
            if (order->getSide() == Side::BUY) {
                trade.buyOrderId = order->getIDNumber();
                trade.sellOrderId = passiveOrder->getIDNumber();
            } else {
                trade.buyOrderId = passiveOrder->getIDNumber();
                trade.sellOrderId = order->getIDNumber();
            }
            
            publisher->publishTrade(trade);
        }
        
        // Remove filled passive order
        if (passiveOrder->getRemainingQuantity() == 0) {
            level->orders.pop_front();
            level->orderIters.erase(passiveOrder->getIDNumber());
            orders.erase(passiveOrder->getIDNumber());
            
            publishOrderEvent(OrderEvent::Type::FILLED, passiveOrder);
            
            if (level->orders.empty()) {
                if (order->getSide() == Side::BUY) {
                    asks.erase(it);
                } else {
                    bids.erase(it);
                }
            }
        } else {
            publishOrderEvent(OrderEvent::Type::PARTIALLY_FILLED, passiveOrder);
        }
    }
    
    // If market order not fully filled, reject remaining quantity
    if (remainingQty > 0) {
        order->reject();
        publishOrderEvent(OrderEvent::Type::REJECTED, order, 
                         "Insufficient liquidity for market order");
    } else {
        publishOrderEvent(OrderEvent::Type::FILLED, order);
    }
    
    invalidateBBO();
}

OrderPointer OrderBook::modifyOrder(IdNumber idNumber, Price newPrice, Quantity newQty) {
    if (!orders.contains(idNumber)) {
        throw std::logic_error("Order does not exist");
    }
    
    OrderPointer oldOrder = orders[idNumber];
    if (oldOrder->getStatus() != Status::PENDING) {
        throw std::logic_error("Order is not pending");
    }
    
    // Create new order with same ID
    auto newOrder = std::make_shared<Order>(
        oldOrder->getIDNumber(),
        oldOrder->getSide(),
        oldOrder->getType(),
        newPrice,
        newQty
    );
    
    cancelOrder(idNumber);
    addOrder(newOrder);
    
    publishOrderEvent(OrderEvent::Type::MODIFIED, newOrder);
    
    return newOrder;
}

void OrderBook::cancelOrder(IdNumber idNumber) {
    if (!orders.contains(idNumber)) {
        throw std::logic_error("Order does not exist");
    }
    
    OrderPointer order = orders[idNumber];
    
    if (order->getStatus() == Status::PARTIALLY_FILLED) {
        throw std::logic_error("Cannot cancel partially filled order");
    }
    
    Side side = order->getSide();
    Price price = order->getPrice();
    
    // Find the order in the correct map
    if (side == Side::BUY) {
        if (bids.contains(price)) {
            PriceLevelPointer level = bids[price];
            
            if (level->orderIters.contains(idNumber)) {
                level->orders.erase(level->orderIters[idNumber]);
                level->orderIters.erase(idNumber);
                
                if (level->orders.empty()) {
                    bids.erase(price);
                }
            }
        }
    } else {
        if (asks.contains(price)) {
            PriceLevelPointer level = asks[price];
            
            if (level->orderIters.contains(idNumber)) {
                level->orders.erase(level->orderIters[idNumber]);
                level->orderIters.erase(idNumber);
                
                if (level->orders.empty()) {
                    asks.erase(price);
                }
            }
        }
    }
    
    orders.erase(idNumber);
    invalidateBBO();
    
    publishOrderEvent(OrderEvent::Type::CANCELED, order);
}

void OrderBook::matchOrders() {
    // Batch matching for limit orders
    while (!bids.empty() && !asks.empty()) {
        PriceLevelPointer bidLevel = bids.begin()->second;
        PriceLevelPointer askLevel = asks.begin()->second;
        
        if (bidLevel->orders.empty() || askLevel->orders.empty()) break;
        if (bidLevel->price < askLevel->price) break;
        
        OrderPointer bidOrder = bidLevel->orders.front();
        OrderPointer askOrder = askLevel->orders.front();
        
        Quantity matchQty = std::min(bidOrder->getRemainingQuantity(), 
                                     askOrder->getRemainingQuantity());
        
        bidOrder->fill(matchQty);
        askOrder->fill(matchQty);
        
        // Publish trade
        if (publisher) {
            Trade trade;
            trade.timestamp = getCurrentTimestamp();
            trade.buyOrderId = bidOrder->getIDNumber();
            trade.sellOrderId = askOrder->getIDNumber();
            trade.executionPrice = askOrder->getPrice();  // Passive order price
            trade.executionQuantity = matchQty;
            trade.aggressorSide = Side::BUY;  // Bid is aggressor if it crossed spread
            
            publisher->publishTrade(trade);
        }
        
        // Remove filled orders
        if (bidOrder->getRemainingQuantity() == 0) {
            bidLevel->orders.pop_front();
            bidLevel->orderIters.erase(bidOrder->getIDNumber());
            orders.erase(bidOrder->getIDNumber());
            
            publishOrderEvent(OrderEvent::Type::FILLED, bidOrder);
            
            if (bidLevel->orders.empty()) {
                bids.erase(bidLevel->price);
            }
        }
        
        if (askOrder->getRemainingQuantity() == 0) {
            askLevel->orders.pop_front();
            askLevel->orderIters.erase(askOrder->getIDNumber());
            orders.erase(askOrder->getIDNumber());
            
            publishOrderEvent(OrderEvent::Type::FILLED, askOrder);
            
            if (askLevel->orders.empty()) {
                asks.erase(askLevel->price);
            }
        }
    }
    
    invalidateBBO();
}

OrderPointer OrderBook::getOrderByID(IdNumber idNumber) const {
    if (!orders.contains(idNumber)) {
        throw std::logic_error("Order does not exist");
    }
    return orders.at(idNumber);
}

bool OrderBook::contains(IdNumber idNumber) const {
    return orders.contains(idNumber);
}

BBO OrderBook::getBBO() const {
    if (!bboDirty) {
        return cachedBBO;
    }
    
    cachedBBO = BBO();
    cachedBBO.timestamp = getCurrentTimestamp();
    
    if (!bids.empty()) {
        const auto& bidLevel = bids.begin()->second;
        cachedBBO.bidPrice = bidLevel->price;
        cachedBBO.bidQty = bidLevel->getSnapshot().totalQuantity;
    }
    
    if (!asks.empty()) {
        const auto& askLevel = asks.begin()->second;
        cachedBBO.askPrice = askLevel->price;
        cachedBBO.askQty = askLevel->getSnapshot().totalQuantity;
    }
    
    bboDirty = false;
    return cachedBBO;
}

L2Snapshot OrderBook::getL2Snapshot(uint32_t depth) const {
    L2Snapshot snapshot;
    snapshot.timestamp = getCurrentTimestamp();
    snapshot.sequenceNumber = ++sequenceNumber;
    
    // Collect bid levels
    uint32_t count = 0;
    for (const auto& [price, level] : bids) {
        if (count >= depth) break;
        snapshot.bids.push_back(level->getSnapshot());
        count++;
    }
    
    // Collect ask levels
    count = 0;
    for (const auto& [price, level] : asks) {
        if (count >= depth) break;
        snapshot.asks.push_back(level->getSnapshot());
        count++;
    }
    
    return snapshot;
}

void OrderBook::publishOrderEvent(OrderEvent::Type type, const OrderPointer& order,
                                  const std::string& reason) {
    if (publisher) {
        OrderEvent event(type, order, getCurrentTimestamp(), reason);
        publisher->publishOrderEvent(event);
    }
}

} // namespace lob
