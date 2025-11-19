#pragma once
#include "Types.h"

namespace lob {

/**
 * @brief Represents an order in the market with support for limit and market orders
 */
class Order {
private:
    IdNumber idNumber;
    Side side;
    OrderType type;
    Price price;
    Quantity initialQuantity;
    Quantity remainingQuantity;
    Status status;

public:
    /**
     * @brief Constructs a new Order object
     * 
     * @param id The unique identifier
     * @param side Buy or sell
     * @param type Limit or market
     * @param price The price (use sentinel values for market orders)
     * @param qty The quantity
     */
    Order(IdNumber id, Side side, OrderType type, Price price, Quantity qty);

    // Getters
    IdNumber getIDNumber() const { return idNumber; }
    Side getSide() const { return side; }
    OrderType getType() const { return type; }
    Price getPrice() const { return price; }
    Quantity getInitialQuantity() const { return initialQuantity; }
    Quantity getRemainingQuantity() const { return remainingQuantity; }
    Quantity getFilledQuantity() const { return initialQuantity - remainingQuantity; }
    Status getStatus() const { return status; }
    
    bool isMarketOrder() const { return type == OrderType::MARKET; }
    bool isLimitOrder() const { return type == OrderType::LIMIT; }

    /**
     * @brief Fills a specified quantity of the order
     * @param qty Quantity to fill
     */
    void fill(Quantity qty);
    
    /**
     * @brief Marks order as rejected (for market orders with no liquidity)
     */
    void reject();
};

} // namespace lob
