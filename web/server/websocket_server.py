#!/usr/bin/env python3
"""
WebSocket Server for Limit Order Book GUI

This Python server acts as a bridge between the C++ orderbook library
and the web-based GUI. It provides real-time market data updates and
handles order submissions from the GUI.

Now using high-performance C++ OrderBook via pybind11 bindings!
"""

import asyncio
import websockets
import json
import random
import time
import sys
import os
from datetime import datetime
from typing import Set, Dict, List

# Add C++ Python module to path
MODULE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'build', 'python')
sys.path.insert(0, os.path.abspath(MODULE_PATH))

# Import C++ OrderBook bindings
try:
    import lob_py
    print("[OK] C++ OrderBook module loaded successfully!")
    USE_CPP_ORDERBOOK = True
except ImportError as e:
    print(f"[WARN] Failed to load C++ OrderBook: {e}")
    print("  Falling back to Python orderbook implementation")
    USE_CPP_ORDERBOOK = False


class OrderBookWrapper:
    """Wrapper that uses C++ OrderBook if available, otherwise Python fallback"""
    
    def __init__(self):
        if USE_CPP_ORDERBOOK:
            self._init_cpp_orderbook()
        else:
            self._init_python_orderbook()
    
    def _init_cpp_orderbook(self):
        """Initialize C++ orderbook"""
        print("Initializing C++ OrderBook...")
        
        self.orderbook = lob_py.OrderBook()
        self.pool = lob_py.OrderPool()
        self.stats = lob_py.MarketStatistics()
        self.publisher = lob_py.TradePublisher()
        
        # Set up publisher
        self.orderbook.set_publisher(self.publisher)
        self.publisher.subscribe(self.stats)
        
        self.next_order_id = 1
        
        # Generate initial market data
        self._generate_cpp_initial_orders()
        
        print(f"  Active Orders: {self.orderbook.get_number_of_orders()}")
        
        # Get initial BBO
        bbo = self.orderbook.get_bbo()
        if bbo.is_valid():
            print(f"  Best Bid: {bbo.bid_price} x {bbo.bid_qty}")
            print(f"  Best Ask: {bbo.ask_price} x {bbo.ask_qty}")
    
    def _generate_cpp_initial_orders(self):
        """Generate sample orders for C++ orderbook"""
        # Generate 10 bid levels
        for i in range(10):
            price = 10000 - (i * 5)
            qty = random.randint(100, 500)
            order = self.pool.create_limit_order(
                self.next_order_id,
                lob_py.Side.BUY,
                price,
                qty
            )
            self.orderbook.add_order(order)
            self.next_order_id += 1
        
        # Generate 10 ask levels
        for i in range(10):
            price = 10010 + (i * 5)
            qty = random.randint(100, 500)
            order = self.pool.create_limit_order(
                self.next_order_id,
                lob_py.Side.SELL,
                price,
                qty
            )
            self.orderbook.add_order(order)
            self.next_order_id += 1
    
    def _init_python_orderbook(self):
        """Initialize Python fallback orderbook"""
        print("Initializing Python OrderBook (fallback)...")
        
        self.next_order_id = 1
        self.total_trades = 0
        self.total_volume = 0
        self.last_price = 10000
        self.active_orders = 0
        
        # Initialize with sample market data
        self.bids = self._generate_side_python(10000, -10, -1)
        self.asks = self._generate_side_python(10010, 10, 1)
        self.active_orders = sum(level['orders'] for level in self.bids + self.asks)
        
        print(f"  Active Orders: {self.active_orders}")
        print(f"  Best Bid: {self.bids[0]['price']} x {self.bids[0]['qty']}")
        print(f"  Best Ask: {self.asks[0]['price']} x {self.asks[0]['qty']}")
    
    def _generate_side_python(self, base_price: int, start_offset: int, direction: int) -> List[Dict]:
        """Generate price levels for Python orderbook"""
        levels = []
        for i in range(10):
            price = base_price + start_offset + (i * 5 * direction)
            qty = random.randint(100, 500)
            orders = random.randint(1, 4)
            levels.append({
                'price': price,
                'qty': qty,
                'orders': orders
            })
        return levels
    
    def get_l2_snapshot(self) -> Dict:
        """Get Level 2 market data snapshot"""
        if USE_CPP_ORDERBOOK:
            snapshot = self.orderbook.get_l2_snapshot(10)
            return {
                'type': 'l2_update',
                'bids': [{'price': level.price, 'qty': level.total_quantity, 'orders': level.order_count} 
                         for level in snapshot.bids],
                'asks': [{'price': level.price, 'qty': level.total_quantity, 'orders': level.order_count}
                         for level in snapshot.asks]
            }
        else:
            return {
                'type': 'l2_update',
                'bids': self.bids,
                'asks': self.asks
            }
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        if USE_CPP_ORDERBOOK:
            return {
                'type': 'stats',
                'totalTrades': self.stats.get_total_trades(),
                'totalVolume': self.stats.get_volume(),
                'activeOrders': self.orderbook.get_number_of_orders()
            }
        else:
            return {
                'type': 'stats',
                'totalTrades': self.total_trades,
                'totalVolume': self.total_volume,
                'activeOrders': self.active_orders
            }
    
    def submit_order(self, side: str, order_type: str, price: int, quantity: int) -> Dict:
        """Submit a new order to the book"""
        if USE_CPP_ORDERBOOK:
            return self._submit_order_cpp(side, order_type, price, quantity)
        else:
            return self._submit_order_python(side, order_type, price, quantity)
    
    def _submit_order_cpp(self, side: str, order_type: str, price: int, quantity: int) -> Dict:
        """Submit order to C++ orderbook"""
        order_id = self.next_order_id
        self.next_order_id += 1
        
        cpp_side = lob_py.Side.BUY if side == 'buy' else lob_py.Side.SELL
        
        print(f"[C++ ORDER] {order_type.upper()} {side.upper()}: {quantity} @ {price if order_type == 'limit' else 'MARKET'}")
        
        try:
            # Create and add order
            if order_type == 'market':
                order = self.pool.create_market_order(order_id, cpp_side, quantity)
            else:
                order = self.pool.create_limit_order(order_id, cpp_side, price, quantity)
            
            self.orderbook.add_order(order)
            
            return {
                'success': True,
                'order_id': order_id,
                'executed': True  # C++ matching happens automatically
            }
        except Exception as e:
            print(f"Error submitting order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _submit_order_python(self, side: str, order_type: str, price: int, quantity: int) -> Dict:
        """Submit order to Python orderbook"""
        order_id = self.next_order_id
        self.next_order_id += 1
        
        print(f"[PYTHON ORDER] {order_type.upper()} {side.upper()}: {quantity} @ {price if order_type == 'limit' else 'MARKET'}")
        
        # Simulate order execution
        if order_type == 'market' or self._will_match_python(side, price):
            # Execute trade
            exec_price = price if order_type == 'limit' else (self.asks[0]['price'] if side == 'buy' else self.bids[0]['price'])
            trade = {
                'type': 'trade',
                'price': exec_price,
                'quantity': quantity,
                'side': side,
                'timestamp': int(time.time() * 1_000_000)
            }
            
            self.total_trades += 1
            self.total_volume += quantity
            self.last_price = exec_price
            
            self._update_levels_after_trade_python(side, exec_price, quantity)
            
            return {
                'success': True,
                'order_id': order_id,
                'executed': True,
                'trade': trade
            }
        else:
            self._add_to_book_python(side, price, quantity)
            self.active_orders += 1
            return {
                'success': True,
                'order_id': order_id,
                'executed': False
            }
    
    def _will_match_python(self, side: str, price: int) -> bool:
        if side == 'buy':
            return price >= self.asks[0]['price']
        else:
            return price <= self.bids[0]['price']
    
    def _update_levels_after_trade_python(self, side: str, price: int, qty: int):
       pass  # Simplified
    
    def _add_to_book_python(self, side: str, price: int, qty: int):
        pass  # Simplified


# WebSocket Server
class WebSocketOrderBookServer:
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.orderbook = OrderBookWrapper()
        
    async def register(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        print(f"[+] Client connected ({len(self.clients)} active)")
        
        # Send initial market snapshot
        await websocket.send(json.dumps(self.orderbook.get_l2_snapshot()))
        await websocket.send(json.dumps(self.orderbook.get_stats()))
    
    async def unregister(self, websocket):
        """Unregister a client"""
        self.clients.remove(websocket)
        print(f"[-] Client disconnected ({len(self.clients)} active)")
    
    async def send_to_all(self, message: str):
        """Broadcast message to all connected clients"""
        if self.clients:
            await asyncio.gather(
                *(client.send(message) for client in self.clients),
                return_exceptions=True
            )
    
    async def handle_client(self, websocket, path):
        """Handle a single client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def process_message(self, websocket, message: str):
        """Process incoming message from client"""
        try:
            data = json.loads(message)
            
            if data.get('type') == 'submit_order':
                result = self.orderbook.submit_order(
                    data.get('side', 'buy'),
                    data.get('orderType', 'limit'),
                    data.get('price', 0),
                    data.get('quantity', 0)
                )
                
                # Send acknowledgment
                await websocket.send(json.dumps({
                    'type': 'order_ack',
                    'success': result['success'],
                    'orderId': result.get('order_id')
                }))
                
                # Broadcast trade if executed
                if result.get('executed') and result.get('trade'):
                    await self.send_to_all(json.dumps(result['trade']))
                
                # Broadcast updated market data
                await self.send_to_all(json.dumps(self.orderbook.get_l2_snapshot()))
                await self.send_to_all(json.dumps(self.orderbook.get_stats()))
                
        except json.JSONDecodeError:
            print("[ERROR] Invalid JSON received")
        except Exception as e:
            print(f"[ERROR] Error processing message: {e}")
    
    async def periodic_updates(self):
        """Send periodic market data updates"""
        while True:
            await asyncio.sleep(0.5)  # Update every 500ms
            
            if self.clients:
                l2_data = json.dumps(self.orderbook.get_l2_snapshot())
                stats_data = json.dumps(self.orderbook.get_stats())
                
                await self.send_to_all(l2_data)
                await self.send_to_all(stats_data)


async def main():
    """Main entry point"""
    print("")
    print("=" * 60)
    print("  Limit Order Book WebSocket Server")
    print(f"  Using: {'C++ OrderBook (pybind11)' if USE_CPP_ORDERBOOK else 'Python OrderBook (fallback)'}")
    print("=" * 60)
    print("")
    
    server = WebSocketOrderBookServer()
    
    print("Starting WebSocket server on ws://localhost:8081...")
    
    # Start WebSocket server
    ws_server = await websockets.serve(
        server.handle_client,
        "localhost",
        8081,
        ping_interval=None
    )
    
    print("[OK] Server started successfully!")
    print("  Clients can connect to: ws://localhost:8081")
    print("  Press Ctrl+C to stop")
    print("")
    
    # Start periodic updates
    asyncio.create_task(server.periodic_updates())
    
    # Run forever
    await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[OK] Server stopped by user")
