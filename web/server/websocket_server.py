#!/usr/bin/env python3
"""
WebSocket Server for Limit Order Book GUI

This Python server acts as a bridge between the C++ orderbook library
and the web-based GUI. It provides real-time market data updates and
handles order submissions from the GUI.
"""

import asyncio
import websockets
import json
import random
import time
from datetime import datetime
from typing import Set, Dict, List

# Simulated orderbook state (in production, this would interface with C++ library via pybind11)
class OrderBook:
    def __init__(self):
        self.next_order_id = 1
        self.total_trades = 0
        self.total_volume = 0
        self.last_price = 10000
        self.active_orders = 0
        
        # Initialize with sample market data
        self.bids = self._generate_side(10000, -10, -1)
        self.asks = self._generate_side(10010, 10, 1)
        self.active_orders = sum(level['orders'] for level in self.bids + self.asks)
        
    def _generate_side(self, base_price: int, start_offset: int, direction: int) -> List[Dict]:
        """Generate price levels for one side of the book"""
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
        return {
            'type': 'l2_update',
            'bids': self.bids,
            'asks': self.asks
        }
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            'type': 'stats',
            'totalTrades': self.total_trades,
            'totalVolume': self.total_volume,
            'activeOrders': self.active_orders
        }
    
    def submit_order(self, side: str, order_type: str, price: int, quantity: int) -> Dict:
        """Submit a new order to the book"""
        order_id = self.next_order_id
        self.next_order_id += 1
        
        print(f"[ORDER] {order_type.upper()} {side.upper()}: {quantity} @ {price if order_type == 'limit' else 'MARKET'}")
        
        # Simulate order execution
        if order_type == 'market' or self._will_match(side, price):
            # Execute trade
            exec_price = price if order_type == 'limit' else (self.asks[0]['price'] if side == 'buy' else self.bids[0]['price'])
            trade = {
                'type': 'trade',
                'price': exec_price,
                'quantity': quantity,
                'side': side,
                'timestamp': int(time.time() * 1_000_000)  # microseconds
            }
            
            self.total_trades += 1
            self.total_volume += quantity
            self.last_price = exec_price
            
            # Update book levels (simplified)
            self._update_levels_after_trade(side, exec_price, quantity)
            
            return {
                'success': True,
                'order_id': order_id,
                'executed': True,
                'trade': trade
            }
        else:
            # Add to book
            self._add_to_book(side, price, quantity)
            self.active_orders += 1
            
            return {
                'success': True,
                'order_id': order_id,
                'executed': False
            }
    
    def _will_match(self, side: str, price: int) -> bool:
        """Check if order will match"""
        if side == 'buy':
            return price >= self.asks[0]['price'] if self.asks else False
        else:
            return price <= self.bids[0]['price'] if self.bids else False
    
    def _update_levels_after_trade(self, side: str, price: int, quantity: int):
        """Update price levels after a trade"""
        levels = self.asks if side == 'buy' else self.bids
        
        if levels:
            levels[0]['qty'] = max(0, levels[0]['qty'] - quantity)
            if levels[0]['qty'] == 0:
                levels.pop(0)
            
        # Add some randomness to other levels
        if random.random() < 0.3:
            self._inject_random_order()
    
    def _add_to_book(self, side: str, price: int, quantity: int):
        """Add order to the book"""
        levels = self.bids if side == 'buy' else self.asks
        
        # Find insertion point and add (simplified - just add to end)
        levels.append({
            'price': price,
            'qty': quantity,
            'orders': 1
        })
        
        # Re-sort
        if side == 'buy':
            levels.sort(key=lambda x: x['price'], reverse=True)
        else:
            levels.sort(key=lambda x: x['price'])
        
        # Keep only top 10 levels
        levels = levels[:10]
        
        if side == 'buy':
            self.bids = levels
        else:
            self.asks = levels
    
    def _inject_random_order(self):
        """Inject random market activity"""
        side = random.choice(['buy', 'sell'])
        base = self.bids[0]['price'] if side == 'buy' else self.asks[0]['price']
        offset = random.randint(-10, 10)
        price = base + offset
        qty = random.randint(50, 200)
        
        self._add_to_book(side, price, qty)
        self.active_orders += 1


# Global state
orderbook = OrderBook()
connected_clients: Set[websockets.WebSocketServerProtocol] = set()


async def broadcast(message: Dict):
    """Broadcast message to all connected clients"""
    if connected_clients:
        message_str = json.dumps(message)
        await asyncio.gather(
            *[client.send(message_str) for client in connected_clients],
            return_exceptions=True
        )


async def handle_client(websocket, path):
    """Handle individual client connection"""
    print(f"[CONNECT] Client connected from {websocket.remote_address}")
    connected_clients.add(websocket)
    
    try:
        # Send initial snapshot to new client
        await websocket.send(json.dumps(orderbook.get_l2_snapshot()))
        await websocket.send(json.dumps(orderbook.get_stats()))
        
        # Handle messages from client
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type')
                
                if msg_type == 'submit_order':
                    side = data.get('side', 'buy')
                    order_type = data.get('orderType', 'limit')
                    price = data.get('price', 0)
                    quantity = data.get('quantity', 0)
                    
                    result = orderbook.submit_order(side, order_type, price, quantity)
                    
                    # Send ack to submitter
                    await websocket.send(json.dumps({
                        'type': 'order_ack',
                        'orderId': result['order_id'],
                        'success': result['success']
                    }))
                    
                    # Broadcast trade if executed
                    if result.get('executed') and 'trade' in result:
                        await broadcast(result['trade'])
                    
                    # Broadcast updated L2 and stats
                    await broadcast(orderbook.get_l2_snapshot())
                    await broadcast(orderbook.get_stats())
                    
            except json.JSONDecodeError:
                print(f"[ERROR] Invalid JSON received")
            except Exception as e:
                print(f"[ERROR] Message handling failed: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        print(f"[DISCONNECT] Client disconnected")
    finally:
        connected_clients.remove(websocket)


async def periodic_updates():
    """Broadcast periodic market data updates"""
    while True:
        await asyncio.sleep(0.5)  # 500ms updates
        
        if connected_clients:
            # Periodically inject random market activity
            if random.random() < 0.2:  # 20% chance every 500ms
                orderbook._inject_random_order()
            
            # Broadcast L2 update
            await broadcast(orderbook.get_l2_snapshot())
            await broadcast(orderbook.get_stats())


async def main():
    """Main server entry point"""
    print("=" * 50)
    print("  Limit Order Book WebSocket Server (Python)")
    print("=" * 50)
    print()
    print(f"Initializing orderbook...")
    print(f"  Active Orders: {orderbook.active_orders}")
    print(f"  Best Bid: {orderbook.bids[0]['price']} x {orderbook.bids[0]['qty']}")
    print(f"  Best Ask: {orderbook.asks[0]['price']} x {orderbook.asks[0]['qty']}")
    print()
    print("Starting WebSocket server on ws://localhost:8081...")
    print("Press Ctrl+C to stop")
    print()
    
    # Start WebSocket server
    async with websockets.serve(handle_client, "localhost", 8081):
        print("[SERVER] WebSocket server started successfully!")
        print("[SERVER] Waiting for connections...")
        print()
        
        # Run periodic updates
        await periodic_updates()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        print("[SERVER] Server stopped successfully!")
