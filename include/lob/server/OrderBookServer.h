#pragma once

#include "lob/core/OrderBook.h"
#include "lob/memory/OrderPool.h"
#include "lob/market_data/Statistics.h"
#include "lob/third_party/json.hpp"

#include "ixwebsocket/IXWebSocketServer.h"
#include "ixwebsocket/IXWebSocket.h"
#include "ixwebsocket/IXConnectionState.h"

#include <set>
#include <mutex>
#include <atomic>
#include <thread>
#include <iostream>
#include <memory>

namespace lob {

using json = nlohmann::json;

/**
 * @brief WebSocket server that integrates OrderBook with web GUI
 * 
 * Features:
 * - Broadcasts L2 market data to all connected clients
 * - Publishes trade events in real-time
 * - Accepts order submissions from clients
 * - Sends performance statistics
 */
class OrderBookServer : public ITradeListener {
private:
    // IXWebSocket server
    ix::WebSocketServer wsServer;
    uint16_t serverPort;
    
    // OrderBook components
    OrderBook* orderBook;
    OrderPool* orderPool;
    MarketStatistics* stats;
    
    // Server state
    std::atomic<bool> running{false};
    std::atomic<uint64_t> nextOrderId{1};
    
public:
    OrderBookServer(OrderBook* ob, OrderPool* pool, MarketStatistics* statistics, uint16_t port = 9090)
        : wsServer(port, "0.0.0.0"), // Bind to all interfaces instead of localhost
          serverPort(port),
          orderBook(ob), orderPool(pool), stats(statistics) {
        
        // Configure WebSocket server
        wsServer.setOnConnectionCallback(
            [this](std::weak_ptr<ix::WebSocket> webSocket,
                   std::shared_ptr<ix::ConnectionState> connectionState) {
                
                auto ws = webSocket.lock();
                if (ws) {
                    std::cout << "Client connected/disconnected event" << std::endl;
                    
                    // Send initial snapshot
                    sendInitialSnapshot(*ws);
                }
            }
        );

        wsServer.setOnClientMessageCallback(
            [this](std::shared_ptr<ix::ConnectionState> connectionState,
                   ix::WebSocket& webSocket,
                   const ix::WebSocketMessagePtr& msg) {
                
                if (msg->type == ix::WebSocketMessageType::Message) {
                    onMessage(webSocket, msg->str);
                } else if (msg->type == ix::WebSocketMessageType::Open) {
                    std::cout << "Client connected" << std::endl;
                    sendInitialSnapshot(webSocket); 
                } else if (msg->type == ix::WebSocketMessageType::Close) {
                    std::cout << "Client disconnected" << std::endl;
                }
            }
        );
    }
    
    /**
     * @brief Start the WebSocket server on specified port
     */
    void start(uint16_t serverPort = 9090) {
        (void)serverPort; // Port is set in constructor now
        running = true;
        std::cout << "WebSocket server starting on port " << this->serverPort << "..." << std::endl;
        
        auto res = wsServer.listenAndStart();
        if (!res) {
            std::cerr << "Server error: failed to listen on port " << this->serverPort << std::endl;
            running = false;
        }
    }
    
    /**
     * @brief Stop the WebSocket server gracefully
     */
    void stop() {
        if (running) {
            running = false;
            wsServer.stop();
            std::cout << "WebSocket server stopped" << std::endl;
        }
    }
    
    /**
     * @brief Broadcast L2 market data snapshot to all clients
     */
    void broadcastL2Update() {
        auto clients = wsServer.getClients();
        if (clients.empty()) return;
        
        L2Snapshot snapshot = orderBook->getL2Snapshot(10);
        
        json message;
        message["type"] = "l2_update";
        
        // Bids
        json bidsArray = json::array();
        for (const auto& level : snapshot.bids) {
            json bid;
            bid["price"] = level.price;
            bid["qty"] = level.totalQuantity;
            bid["orders"] = level.orderCount;
            bidsArray.push_back(bid);
        }
        message["bids"] = bidsArray;
        
        // Asks
        json asksArray = json::array();
        for (const auto& level : snapshot.asks) {
            json ask;
            ask["price"] = level.price;
            ask["qty"] = level.totalQuantity;
            ask["orders"] = level.orderCount;
            asksArray.push_back(ask);
        }
        message["asks"] = asksArray;
        
        broadcast(message.dump());
    }
    
    /**
     * @brief Broadcast performance statistics to all clients
     */
    void broadcastStats() {
        auto clients = wsServer.getClients();
        if (clients.empty()) return;
        
        json message;
        message["type"] = "stats";
        message["totalTrades"] = stats->getTotalTrades();
        message["totalVolume"] = stats->getVolume();
        message["activeOrders"] = orderBook->getNumberOfOrders();
        
        broadcast(message.dump());
    }
    
    /**
     * @brief TradeListener callback - called when trade executes
     */
    void onTrade(const Trade& trade) override {
        auto clients = wsServer.getClients();
        if (clients.empty()) return;
        
        json message;
        message["type"] = "trade";
        message["price"] = trade.executionPrice;
        message["quantity"] = trade.executionQuantity;
        message["side"] = (trade.aggressorSide == Side::BUY) ? "buy" : "sell";
        message["timestamp"] = trade.timestamp;
        
        broadcast(message.dump());
    }

    /**
     * @brief Handle order events (optional for now)
     */
    void onOrderEvent(const OrderEvent& event) override {
        // Can implement order updates here if needed
        (void)event;
    }
    
    bool isRunning() const { return running; }
    
private:
    
    void sendInitialSnapshot(ix::WebSocket& ws) {
        try {
            L2Snapshot snapshot = orderBook->getL2Snapshot(10);
            json message;
            message["type"] = "l2_update";
            
            json bidsArray = json::array();
            for (const auto& level : snapshot.bids) {
                json bid;
                bid["price"] = level.price;
                bid["qty"] = level.totalQuantity;
                bid["orders"] = level.orderCount;
                bidsArray.push_back(bid);
            }
            message["bids"] = bidsArray;
            
            json asksArray = json::array();
            for (const auto& level : snapshot.asks) {
                json ask;
                ask["price"] = level.price;
                ask["qty"] = level.totalQuantity;
                ask["orders"] = level.orderCount;
                asksArray.push_back(ask);
            }
            message["asks"] = asksArray;
            
            ws.send(message.dump());
        } catch (const std::exception& e) {
            std::cerr << "Failed to send initial snapshot: " << e.what() << std::endl;
        }
    }

    /**
     * @brief Handle incoming message from client
     */
    void onMessage(ix::WebSocket& ws, const std::string& msg) {
        try {
            json data = json::parse(msg);
            
            std::string type = data.value("type", "");
            
            if (type == "submit_order") {
                handleOrderSubmission(ws, data);
            }
        } catch (const std::exception& e) {
            std::cerr << "Message handling error: " << e.what() << std::endl;
        }
    }
    
    /**
     * @brief Process order submission from client
     */
    void handleOrderSubmission(ix::WebSocket& ws, const json& data) {
        try {
            std::string sideStr = data.value("side", "buy");
            std::string typeStr = data.value("orderType", "limit");
            Price price = data.value("price", 0);
            Quantity quantity = data.value("quantity", 0);
            
            if (quantity <= 0) {
                sendError(ws, "Invalid quantity");
                return;
            }
            
            Side side = (sideStr == "buy") ? Side::BUY : Side::SELL;
            IdNumber orderId = nextOrderId++;
            
            OrderPointer order;
            
            if (typeStr == "market") {
                order = orderPool->createMarketOrder(orderId, side, quantity);
                std::cout << "Market " << sideStr << " order: " << quantity << " units" << std::endl;
            } else {
                if (price <= 0) {
                    sendError(ws, "Invalid price for limit order");
                    return;
                }
                order = orderPool->createLimitOrder(orderId, side, price, quantity);
                std::cout << "Limit " << sideStr << " order: " << quantity << " @ " << price << std::endl;
            }
            
            // Add order to book (will trigger matching and trade callbacks)
            orderBook->addOrder(order);
            
            // Send acknowledgment
            json response;
            response["type"] = "order_ack";
            response["orderId"] = orderId;
            response["success"] = true;
            ws.send(response.dump());
            
            // Broadcast updated L2 data
            broadcastL2Update();
            broadcastStats();
            
        } catch (const std::exception& e) {
            sendError(ws, std::string("Order submission failed: ") + e.what());
        }
    }
    
    /**
     * @brief Send error message to specific client
     */
    void sendError(ix::WebSocket& ws, const std::string& errorMsg) {
        json response;
        response["type"] = "error";
        response["message"] = errorMsg;
        try {
            ws.send(response.dump());
        } catch (...) {}
    }
    
    /**
     * @brief Broadcast message to all connected clients
     */
    void broadcast(const std::string& message) {
        auto clients = wsServer.getClients();
        for (auto& client : clients) {
            client->send(message);
        }
    }
};

} // namespace lob
