#include "lob/core/Order.h"
#include <stdexcept>

namespace lob {

Order::Order(IdNumber id, Side side, OrderType type, Price price, Quantity qty)
    : idNumber(id),
      side(side),
      type(type),
      price(price),
      initialQuantity(qty),
      remainingQuantity(qty),
      status(Status::PENDING)
{
    // Validate market order prices
    if (type == OrderType::MARKET) {
        if (side == Side::BUY) {
            this->price = MARKET_BUY_PRICE;
        } else {
            this->price = MARKET_SELL_PRICE;
        }
    }
}

void Order::fill(Quantity qty) {
    if (qty > remainingQuantity) {
        throw std::logic_error("Cannot fill more than remaining quantity");
    }
    
    remainingQuantity -= qty;
    
    if (remainingQuantity == 0) {
        status = Status::COMPLETELY_FILLED;
    } else {
        status = Status::PARTIALLY_FILLED;
    }
}

void Order::reject() {
    status = Status::REJECTED;
}

} // namespace lob
