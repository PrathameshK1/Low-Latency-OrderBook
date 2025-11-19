#include "lob/core/OrderBook.h"
#include "lob/memory/OrderPool.h"
#include "lob/market_data/Statistics.h"
#include "lob/server/OrderBookServer.h"

#include <iostream>
#include <random>
#include <csignal>
#include <thread>
#include <atomic>
#include <chrono>

using namespace lob;

// Global flag for graceful shutdown
std::atomic<bool> keepRunning{true};

void signalHandler(int signum) {
    std::cout << "\nReceived shutdown signal (" << signum << ")" << std::endl;
    keepRunning = false;
}

/**
 * @brief Generate sample market data to populate the orderbook
 */
void generateSampleOrders(OrderBook& book, OrderPool& pool, uint64_t& nextOrderId) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> priceDist(9900, 10100);
    std::uniform_int_distribution<> qtyDist(50, 500);
    
    const Price basePrice = 10000;
    
    // Generate bid orders (below mid price)
    for (int i = 0; i < 15; i++) {
        Price price = basePrice - (i * 5) - (std::rand() % 10);
        Quantity qty = qtyDist(gen);
        auto order = pool.createLimitOrder(nextOrderId++, Side::BUY, price, qty);
        book.addOrder(order);
    }
    
    // Generate ask orders (above mid price)
    for (int i = 0; i < 15; i++) {
        Price price = basePrice + 10 + (i * 5) + (std::rand() % 10);
        Quantity qty = qtyDist(gen);
        auto order = pool.createLimitOrder(nextOrderId++, Side::SELL, price, qty);
        book.addOrder(order);
    }
    
    std::cout << "Generated " << book.getNumberOfOrders() << " sample orders" << std::endl;
}

/**
 * @brief Periodically inject random orders to simulate market activity
 */
void injectMarketActivity(OrderBook& book, OrderPool& pool, uint64_t& nextOrderId) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> sideDist(0, 1);
    std::uniform_int_distribution<> typeDist(0, 4); // 80% limit, 20% market
    std::uniform_int_distribution<> qtyDist(10, 200);
    
    // Get current BBO to price orders sensibly
    BBO bbo = book.getBBO();
    if (!bbo.isValid()) return;
    
    Side side = (sideDist(gen) == 0) ? Side::BUY : Side::SELL;
    Quantity qty = qtyDist(gen);
    
    if (typeDist(gen) == 0) {
        // Market order (20% chance) - will execute immediately
        auto order = pool.createMarketOrder(nextOrderId++, side, qty);
        book.addOrder(order);
    } else {
        // Limit order (80% chance)
        Price price;
        if (side == Side::BUY) {
            // Place buy order near or below best bid
            std::uniform_int_distribution<> offsetDist(-20, 5);
            price = bbo.bidPrice + offsetDist(gen);
        } else {
            // Place sell order near or above best ask
            std::uniform_int_distribution<> offsetDist(-5, 20);
            price = bbo.askPrice + offsetDist(gen);
        }
        
        auto order = pool.createLimitOrder(nextOrderId++, side, price, qty);
        book.addOrder(order);
    }
}

int main() {
    std::cout << "==========================================" << std::endl;
    std::cout << "  Limit Order Book WebSocket Server" << std::endl;
    std::cout << "==========================================" << std::endl;
    std::cout << std::endl;
    
    // Register signal handler for Ctrl+C
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);
    
    // Initialize components
    std::cout << "Initializing orderbook..." << std::endl;
    OrderPool pool;
    OrderBook book;
    TradePublisher publisher;
    MarketStatistics stats;
    
    // Connect components
    book.setPublisher(&publisher);
    publisher.subscribe(&stats);
    
    // Create WebSocket server
    OrderBookServer server(&book, &pool, &stats);
    publisher.subscribe(&server);  // Server listens for trade events
    
    std::cout << "Generating sample market data..." << std::endl;
    uint64_t nextOrderId = 1;
    generateSampleOrders(book, pool, nextOrderId);
    
    // Display initial state
    BBO bbo = book.getBBO();
    std::cout << "\nInitial Market State:" << std::endl;
    std::cout << "  Best Bid: " << bbo.bidPrice << " x " << bbo.bidQty << std::endl;
    std::cout << "  Best Ask: " << bbo.askPrice << " x " << bbo.askQty << std::endl;
    std::cout << "  Spread: " << bbo.spread() << std::endl;
    std::cout << "  Active Orders: " << book.getNumberOfOrders() << std::endl;
    std::cout << std::endl;
    
    // Start WebSocket server in a separate thread
    std::cout << "Starting WebSocket server on port 8080..." << std::endl;
    std::thread serverThread([&server]() {
        server.start(8080);
    });
    
    // Give server time to start
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    
    if (server.isRunning()) {
        std::cout << "Server started successfully!" << std::endl;
        std::cout << "Broadcasting L2 updates every 500ms" << std::endl;
        std::cout << "Press Ctrl+C to stop" << std::endl;
        std::cout << std::endl;
    } else {
        std::cerr << "Failed to start server!" << std::endl;
        return 1;
    }
    
    // Main loop: broadcast updates and inject market activity
    auto lastBroadcast = std::chrono::steady_clock::now();
    auto lastActivity = std::chrono::steady_clock::now();
    
    while (keepRunning && server.isRunning()) {
        auto now = std::chrono::steady_clock::now();
        
        // Broadcast L2 update every 500ms
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - lastBroadcast).count() >= 500) {
            server.broadcastL2Update();
            server.broadcastStats();
            lastBroadcast = now;
        }
        
        // Inject random market activity every 3-5 seconds
        auto activityDelay = std::chrono::seconds(3 + (std::rand() % 3));
        if (std::chrono::duration_cast<std::chrono::seconds>(now - lastActivity) >= activityDelay) {
            injectMarketActivity(book, pool, nextOrderId);
            lastActivity = now;
        }
        
        // Sleep to avoid busy-waiting
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    // Graceful shutdown
    std::cout << "\nShutting down server..." << std::endl;
    server.stop();
    
    if (serverThread.joinable()) {
        serverThread.join();
    }
    
    // Display final statistics
    std::cout << "\n--- Final Statistics ---" << std::endl;
    std::cout << "Total Trades: " << stats.getTotalTrades() << std::endl;
    std::cout << "Total Volume: " << stats.getVolume() << std::endl;
    std::cout << "Active Orders: " << book.getNumberOfOrders() << std::endl;
    if (stats.getTotalTrades() > 0) {
        std::cout << "VWAP: " << stats.getVWAP() << std::endl;
        std::cout << "Last Price: " << stats.getLastPrice() << std::endl;
    }
    std::cout << std::endl;
    std::cout << "Server stopped successfully!" << std::endl;
    
    return 0;
}
