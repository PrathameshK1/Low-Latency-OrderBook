// Basic C++ demo - simplified version to test the orderbook
// A full WebSocket server with libwebsockets will be added next

#include "lob/core/OrderBook.h"
#include "lob/memory/OrderPool.h"
#include "lob/market_data/Statistics.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <random>

using namespace lob;
using namespace std::chrono_literals;

int main() {
    std::cout << "\n==============================================\n";
    std::cout << "    Limit Order Book - Basic Demo\n";
    std::cout << "==============================================\n\n";

    // Create components
    OrderPool pool;
    OrderBook book;
    TradePublisher publisher;
    MarketStatistics stats;

    // Connect components
    book.setPublisher(&publisher);
    publisher.subscribe(&stats);

    std::cout << "✓ Initialized OrderBook with memory pool\n";
    std::cout << "✓ Connected trade statistics collector\n\n";

    // Generate some sample orders
    std::random_device rd;
    std::mt19937 rng(rd());
    std::uniform_int_distribution<int> priceDist(9950, 10050);
    std::uniform_int_distribution<int> qtyDist(10, 500);
    std::uniform_int_distribution<int> sideDist(0, 1);

    std::cout << "Generating sample orders...\n\n";

    IdNumber nextId = 1;

    // Add some limit orders to build the book
    for (int i = 0; i < 20; ++i) {
        Side side = (sideDist(rng) == 0) ? Side::BUY : Side::SELL;
        Price price = priceDist(rng);
        Quantity qty = qtyDist(rng);

        auto order = pool.createLimitOrder(nextId++, side, price, qty);
        book.addOrder(order);
    }

    // Add a market order to trigger some trades
    auto marketOrder = pool.createMarketOrder(nextId++, Side::BUY, 1000);
    std::cout << "Executing market BUY order for 1000 units...\n";
    book.addOrder(marketOrder);

    // Match remaining limit orders
    book.matchOrders();

    // Display statistics
    std::cout << "\n--- Order Book Statistics ---\n";
    std::cout << "Total Orders: " << book.getNumberOfOrders() << "\n";
    std::cout << "Total Trades: " << stats.getTotalTrades() << "\n";
    std::cout << "Total Volume: " << stats.getVolume() << "\n";
    std::cout << "Last Price: " << stats.getLastPrice() << "\n";
    std::cout << "VWAP: " << stats.getVWAP() << "\n";

    // Display BBO
    BBO bbo = book.getBBO();
    std::cout << "\n--- Best Bid/Offer ---\n";
    std::cout << "Bid: " << bbo.bidPrice << " x " << bbo.bidQty << "\n";
    std::cout << "Ask: " << bbo.askPrice << " x " << bbo.askQty << "\n";
    std::cout << "Spread: " << bbo.spread() << "\n";
    std::cout << "Mid: " << bbo.midPrice() << "\n";

    // Display L2 data
    L2Snapshot snapshot = book.getL2Snapshot(5);
    std::cout << "\n--- L2 Market Data (Top 5 Levels) ---\n";
    std::cout << "\nBIDS:\n";
    for (const auto& level : snapshot.bids) {
        std::cout << "  " << level.price << "  |  " 
                  << level.totalQuantity << "  (" 
                  << level.orderCount << " orders)\n";
    }
    std::cout << "\nASKS:\n";
    for (const auto& level : snapshot.asks) {
        std::cout << "  " << level.price << "  |  " 
                  << level.totalQuantity << "  (" 
                  << level.orderCount << " orders)\n";
    }

    // Display recent trades
    auto recentTrades = stats.getRecentTrades(5);
    std::cout << "\n--- Recent Trades ---\n";
    for (const auto& trade : recentTrades) {
        std::cout << "  " << trade.executionPrice << " x " 
                  << trade.executionQuantity 
                  << " [" << (trade.aggressorSide == Side::BUY ? "BUY" : "SELL") << "]\n";
    }

    // Memory pool stats
    std::cout << "\n--- Memory Pool Statistics ---\n";
    std::cout << "Allocated Orders: " << pool.allocated() << "\n";
    std::cout << "Pool Capacity: " << pool.capacity() << "\n";
    std::cout << "Utilization: " << pool.utilization() << "%\n";
    std::cout << "Blocks: " << pool.blockCount() << "\n";

    std::cout << "\n==============================================\n";
    std::cout << "✓ Demo completed successfully!\n";
    std::cout << "==============================================\n\n";

    return 0;
}
