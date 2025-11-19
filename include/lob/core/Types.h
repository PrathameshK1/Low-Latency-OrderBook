#pragma once
#include <cstdint>
#include <memory>
#include <limits>

namespace lob {

/**
 * @brief Order side: buy or sell
 */
enum class Side { 
    BUY, 
    SELL 
};

/**
 * @brief Order type: limit (rests in book) or market (executes immediately)
 */
enum class OrderType {
    LIMIT,   // Rests in book at specified price
    MARKET   // Executes immediately at best available price
};

/**
 * @brief Order status lifecycle
 */
enum class Status {
    PENDING,
    PARTIALLY_FILLED,
    COMPLETELY_FILLED,
    REJECTED  // For market orders with no liquidity
};

// Type aliases for clarity and performance
using IdNumber = std::uint64_t;
using Price = std::uint32_t;
using Quantity = std::uint32_t;
using TradeId = std::uint64_t;
using Timestamp = std::uint64_t;

// Sentinel prices for market orders
constexpr Price MARKET_BUY_PRICE = std::numeric_limits<Price>::max();
constexpr Price MARKET_SELL_PRICE = 0;

// Forward declarations
class Order;
using OrderPointer = std::shared_ptr<Order>;

} // namespace lob
