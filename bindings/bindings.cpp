#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "lob/core/OrderBook.h"
#include "lob/core/Order.h"
#include "lob/memory/OrderPool.h"
#include "lob/market_data/L2Data.h"
#include "lob/market_data/Statistics.h"
#include "lob/market_data/TradeListener.h"

namespace py = pybind11;
using namespace lob;

PYBIND11_MODULE(lob_py, m) {
    m.doc() = "Python bindings for high-performance C++ OrderBook";
    
    // Expose Side enum
    py::enum_<Side>(m, "Side")
        .value("BUY", Side::BUY)
        .value("SELL", Side::SELL)
        .export_values();
    
    // Expose OrderType enum
    py::enum_<OrderType>(m, "OrderType")
        .value("LIMIT", OrderType::LIMIT)
        .value("MARKET", OrderType::MARKET)
        .export_values();
    
    // Expose Order class
    py::class_<Order, std::shared_ptr<Order>>(m, "Order")
        .def_property_readonly("id", &Order::getIDNumber)
        .def_property_readonly("side", &Order::getSide)
        .def_property_readonly("type", &Order::getType)
        .def_property_readonly("price", &Order::getPrice)
        .def_property_readonly("initial_quantity", &Order::getInitialQuantity)
        .def_property_readonly("filled_quantity", &Order::getFilledQuantity)
        .def_property_readonly("remaining_quantity", &Order::getRemainingQuantity)
        .def_property_readonly("status", &Order::getStatus)
        .def("is_market_order", &Order::isMarketOrder)
        .def("is_limit_order", &Order::isLimitOrder);
    
    // Expose PriceLevel struct
    py::class_<PriceLevel>(m, "PriceLevel")
        .def_readonly("price", &PriceLevel::price)
        .def_readonly("total_quantity", &PriceLevel::totalQuantity)
        .def_readonly("order_count", &PriceLevel::orderCount);
    
    // Expose L2Snapshot struct
    py::class_<L2Snapshot>(m, "L2Snapshot")
        .def_readonly("bids", &L2Snapshot::bids)
        .def_readonly("asks", &L2Snapshot::asks)
        .def_readonly("timestamp", &L2Snapshot::timestamp)
        .def("get_bbo", &L2Snapshot::getBBO);
    
    // Expose BBO struct
    py::class_<BBO>(m, "BBO")
        .def_readonly("bid_price", &BBO::bidPrice)
        .def_readonly("bid_qty", &BBO::bidQty)
        .def_readonly("ask_price", &BBO::askPrice)
        .def_readonly("ask_qty", &BBO::askQty)
        .def_readonly("timestamp", &BBO::timestamp)
        .def("spread", &BBO::spread)
        .def("mid_price", &BBO::midPrice)
        .def("imbalance", &BBO::imbalance)
        .def("is_valid", &BBO::isValid);
    
    // Expose Trade struct
    py::class_<Trade>(m, "Trade")
        .def_readonly("execution_price", &Trade::executionPrice)
        .def_readonly("execution_quantity", &Trade::executionQuantity)
        .def_readonly("aggressor_side", &Trade::aggressorSide)
        .def_readonly("buy_order_id", &Trade::buyOrderId)
        .def_readonly("sell_order_id", &Trade::sellOrderId)
        .def_readonly("timestamp", &Trade::timestamp);
    
    // Expose OrderPool class
    py::class_<OrderPool>(m, "OrderPool")
        .def(py::init<>())
        .def("create_limit_order", &OrderPool::createLimitOrder,
             py::arg("id"), py::arg("side"), py::arg("price"), py::arg("quantity"))
        .def("create_market_order", &OrderPool::createMarketOrder,
             py::arg("id"), py::arg("side"), py::arg("quantity"))
        .def("allocated", &OrderPool::allocated)
        .def("capacity", &OrderPool::capacity)
        .def("utilization", &OrderPool::utilization);
    
    // Expose TradePublisher class
    py::class_<TradePublisher>(m, "TradePublisher")
        .def(py::init<>())
        .def("subscribe", &TradePublisher::subscribe)
        .def("unsubscribe", &TradePublisher::unsubscribe)
        .def("publish_trade", &TradePublisher::publishTrade)
        .def("publish_order_event", &TradePublisher::publishOrderEvent);
    
    // Expose MarketStatistics class
    py::class_<MarketStatistics>(m, "MarketStatistics")
        .def(py::init<>())
        .def("on_trade", &MarketStatistics::onTrade)
        .def("on_order_event", &MarketStatistics::onOrderEvent)
        .def("get_total_trades", &MarketStatistics::getTotalTrades)
        .def("get_volume", &MarketStatistics::getVolume)
        .def("get_vwap", &MarketStatistics::getVWAP)
        .def("reset", &MarketStatistics::reset);
    
    // Expose OrderBook class
    py::class_<OrderBook>(m, "OrderBook")
        .def(py::init<>())
        .def("set_publisher", &OrderBook::setPublisher)
        .def("add_order", &OrderBook::addOrder)
        .def("cancel_order", &OrderBook::cancelOrder)
        .def("get_l2_snapshot", &OrderBook::getL2Snapshot, py::arg("depth") = 10)
        .def("get_bbo", &OrderBook::getBBO)
        .def("get_number_of_orders", &OrderBook::getNumberOfOrders);
}
