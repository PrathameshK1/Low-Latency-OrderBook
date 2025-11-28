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

# Add MinGW bin directory to PATH for DLL dependencies (Windows)
if sys.platform == 'win32':
    # Common MinGW installation locations
    possible_mingw_paths = [
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin"),
        r"C:\ProgramData\mingw64\mingw64\bin",
        r"C:\mingw64\bin",
        r"C:\msys64\mingw64\bin",
    ]
    
    for mingw_bin in possible_mingw_paths:
        if os.path.exists(mingw_bin):
            os.environ['PATH'] = mingw_bin + os.pathsep + os.environ.get('PATH', '')
            break

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
        
        # Initialize trade count after initial orders (they might create trades)
        self.last_trade_count = self.stats.get_total_trades()
        
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
        
        # Get orderbook state before adding
        orders_before = self.orderbook.get_number_of_orders()
        bbo_before = self.orderbook.get_bbo()
        
        print(f"[C++ ORDER] {order_type.upper()} {side.upper()}: {quantity} @ {price if order_type == 'limit' else 'MARKET'}")
        print(f"  Before: {orders_before} orders, BBO: {bbo_before.bid_price}/{bbo_before.ask_price}")
        
        try:
            # Create and add order
            if order_type == 'market':
                order = self.pool.create_market_order(order_id, cpp_side, quantity)
            else:
                order = self.pool.create_limit_order(order_id, cpp_side, price, quantity)
            
            self.orderbook.add_order(order)
            
            # Get orderbook state after adding
            orders_after = self.orderbook.get_number_of_orders()
            bbo_after = self.orderbook.get_bbo()
            
            print(f"  After: {orders_after} orders, BBO: {bbo_after.bid_price}/{bbo_after.ask_price}")
            
            # Check if order was matched (order count might decrease if fully matched)
            if orders_after < orders_before:
                print(f"  [MATCHED] Order was fully matched")
            elif orders_after == orders_before:
                print(f"  [ADDED] Order added to book (no match)")
            else:
                print(f"  [ADDED] Order added to book")
            
            # Check if trades occurred and get new ones
            trades = []
            current_trade_count = self.stats.get_total_trades()
            if current_trade_count > self.last_trade_count:
                # New trades occurred, get only the new ones
                num_new_trades = current_trade_count - self.last_trade_count
                print(f"  [TRADE DETECT] Found {num_new_trades} new trade(s) (total: {current_trade_count}, last: {self.last_trade_count})")
                recent_trades = self.stats.get_recent_trades(num_new_trades)
                for trade in recent_trades:
                    trades.append({
                        'type': 'trade',
                        'price': trade.execution_price,
                        'quantity': trade.execution_quantity,
                        'side': 'buy' if trade.aggressor_side == lob_py.Side.BUY else 'sell',
                        'timestamp': trade.timestamp
                    })
                self.last_trade_count = current_trade_count
            
            return {
                'success': True,
                'order_id': order_id,
                'executed': orders_after <= orders_before,  # True if matched immediately
                'trades': trades  # List of trades that occurred
            }
        except Exception as e:
            print(f"  [ERROR] Error submitting order: {e}")
            import traceback
            traceback.print_exc()
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
        # Track last trade count for periodic updates
        if USE_CPP_ORDERBOOK and hasattr(self.orderbook, 'stats'):
            self.last_periodic_trade_count = self.orderbook.stats.get_total_trades()
        else:
            self.last_periodic_trade_count = 0
        
        # Performance metrics tracking
        self.performance_metrics = {
            'orders_processed': 0,
            'trades_executed': 0,
            'start_time': time.time(),
            'last_update_time': time.time(),
            'orders_per_second': 0.0,
            'trades_per_second': 0.0,
            'avg_latency_us': 0.0,
            'peak_orders_per_second': 0.0,
            'peak_trades_per_second': 0.0,
            'total_orders': 0,
            'total_trades': 0
        }
        self.latency_samples = []  # Store recent latency samples
        self.max_latency_samples = 1000
        
        # Auto-order generation for continuous activity
        self.auto_generate_enabled = True
        self.auto_generate_rate = 100  # Orders per second
        self.auto_generate_task = None
        
    async def register(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        print(f"[+] Client connected ({len(self.clients)} active)")
        
        try:
            # Send initial market snapshot
            await websocket.send(json.dumps(self.orderbook.get_l2_snapshot()))
            await websocket.send(json.dumps(self.orderbook.get_stats()))
            await websocket.send(json.dumps(self.get_performance_metrics()))
        except Exception as e:
            print(f"[ERROR] Failed to send initial data to client: {e}")
    
    async def unregister(self, websocket):
        """Unregister a client"""
        self.clients.remove(websocket)
        print(f"[-] Client disconnected ({len(self.clients)} active)")
    
    async def send_to_all(self, message: str):
        """Broadcast message to all connected clients with error handling"""
        if self.clients:
            results = await asyncio.gather(
                *(client.send(message) for client in self.clients),
                return_exceptions=True
            )
            # Remove disconnected clients
            disconnected = []
            for i, (client, result) in enumerate(zip(self.clients, results)):
                if isinstance(result, Exception):
                    disconnected.append(client)
            for client in disconnected:
                try:
                    self.clients.remove(client)
                except KeyError:
                    pass
    
    async def handle_client(self, websocket, path=None):
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
            # Ensure message is a string and parse it
            if isinstance(message, str):
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Invalid JSON: {str(e)}'
                    }))
                    return
            elif isinstance(message, dict):
                data = message
            else:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid message format'
                }))
                return
            
            # Ensure data is a dict
            if not isinstance(data, dict):
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Message must be a JSON object'
                }))
                return
            
            if data.get('type') == 'submit_batch':
                # Batch order submission for high throughput
                orders = data.get('orders', [])
                if not orders:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'No orders in batch'
                    }))
                    return
                
                process_start = time.perf_counter()
                results = []
                trades_batch = []
                
                for order_data in orders:
                    result = self.orderbook.submit_order(
                        order_data.get('side', 'buy'),
                        order_data.get('orderType', 'limit'),
                        order_data.get('price', 0),
                        order_data.get('quantity', 0)
                    )
                    results.append(result)
                    if result.get('trades'):
                        trades_batch.extend(result.get('trades', []))
                
                process_latency = (time.perf_counter() - process_start) * 1_000_000
                self.latency_samples.append(process_latency / len(orders))  # Average latency per order
                if len(self.latency_samples) > self.max_latency_samples:
                    self.latency_samples.pop(0)
                
                # Update metrics
                self.performance_metrics['orders_processed'] += len(orders)
                self.performance_metrics['total_orders'] += len(orders)
                if trades_batch:
                    self.performance_metrics['trades_executed'] += len(trades_batch)
                    self.performance_metrics['total_trades'] += len(trades_batch)
                
                # Send batch acknowledgment
                await websocket.send(json.dumps({
                    'type': 'batch_ack',
                    'success': True,
                    'orders_processed': len(orders),
                    'trades_executed': len(trades_batch),
                    'latency_us': round(process_latency, 2)
                }))
                
                # Broadcast all trades immediately
                for trade in trades_batch:
                    await self.send_to_all(json.dumps(trade))
                
                # Broadcast updated market data and performance metrics
                l2_snapshot = self.orderbook.get_l2_snapshot()
                stats = self.orderbook.get_stats()
                perf = self.get_performance_metrics()
                await self.send_to_all(json.dumps(l2_snapshot))
                await self.send_to_all(json.dumps(stats))
                await self.send_to_all(json.dumps(perf))
                
            elif data.get('type') == 'stress_test':
                # EXTREME Stress test - generate 10+ million orders per second
                num_orders = data.get('num_orders', 1000)
                side = data.get('side', 'buy')
                order_type = data.get('orderType', 'limit')
                base_price = data.get('base_price', 10000)
                price_range = data.get('price_range', 100)
                qty_range = data.get('qty_range', (10, 1000))
                
                print(f"[STRESS TEST] Generating {num_orders} orders at EXTREME throughput...")
                process_start = time.perf_counter()
                
                # EXTREME MODE: Process orders in massive parallel batches
                # Target: 10+ million orders per second
                batch_size = 10000  # Larger batches for extreme throughput
                total_trades = 0
                update_interval = 10000  # Update every 10k orders
                
                # Send stress test start notification
                await self.send_to_all(json.dumps({
                    'type': 'stress_test_start',
                    'num_orders': num_orders
                }))
                
                for i in range(0, num_orders, batch_size):
                    batch_end = min(i + batch_size, num_orders)
                    batch_start_time = time.perf_counter()
                    
                    # Process batch as fast as possible
                    for j in range(i, batch_end):
                        price = base_price + random.randint(-price_range, price_range) if order_type == 'limit' else 0
                        qty = random.randint(qty_range[0], qty_range[1])
                        order_side = side if j % 2 == 0 else ('sell' if side == 'buy' else 'buy')
                        
                        # Submit order (minimal overhead)
                        order_start = time.perf_counter()
                        result = self.orderbook.submit_order(
                            order_side,
                            order_type,
                            price,
                            qty
                        )
                        order_latency = (time.perf_counter() - order_start) * 1_000_000
                        
                        # Update metrics (minimal operations)
                        if len(self.latency_samples) < self.max_latency_samples:
                            self.latency_samples.append(order_latency)
                        else:
                            self.latency_samples[random.randint(0, self.max_latency_samples - 1)] = order_latency
                        
                        self.performance_metrics['orders_processed'] += 1
                        self.performance_metrics['total_orders'] += 1
                        
                        if result.get('trades'):
                            trade_count = len(result.get('trades', []))
                            total_trades += trade_count
                            self.performance_metrics['trades_executed'] += trade_count
                            self.performance_metrics['total_trades'] += trade_count
                            
                            # Broadcast trades (non-blocking batch)
                            for trade in result['trades']:
                                trade['stress_test'] = True
                                await self.send_to_all(json.dumps(trade))
                    
                    # Send high-frequency updates during stress test for visual feedback
                    if (i + batch_size) % update_interval == 0 or i + batch_size >= num_orders:
                        batch_time = time.perf_counter() - batch_start_time
                        batch_ops = batch_size / batch_time if batch_time > 0 else 0
                        
                        l2_snapshot = self.orderbook.get_l2_snapshot()
                        stats = self.orderbook.get_stats()
                        perf = self.get_performance_metrics()
                        
                        # Send updates in parallel
                        await asyncio.gather(
                            self.send_to_all(json.dumps(l2_snapshot)),
                            self.send_to_all(json.dumps(stats)),
                            self.send_to_all(json.dumps(perf)),
                            return_exceptions=True
                        )
                        
                        print(f"[STRESS TEST] Progress: {i + batch_size}/{num_orders} ({batch_ops:.0f} ops/sec)")
                
                process_time = time.perf_counter() - process_start
                orders_per_sec = num_orders / process_time if process_time > 0 else 0
                
                print(f"[STRESS TEST] COMPLETED: {num_orders} orders in {process_time:.2f}s")
                print(f"[STRESS TEST] Throughput: {orders_per_sec:,.0f} orders/sec")
                print(f"[STRESS TEST] Generated {total_trades} trades")
                
                # Send final results
                await websocket.send(json.dumps({
                    'type': 'stress_test_result',
                    'orders_processed': num_orders,
                    'trades_executed': total_trades,
                    'time_seconds': round(process_time, 2),
                    'orders_per_second': round(orders_per_sec, 2)
                }))
                
                # Send stress test end notification
                await self.send_to_all(json.dumps({
                    'type': 'stress_test_end',
                    'orders_per_second': round(orders_per_sec, 2)
                }))
                
                # Broadcast final updated data
                l2_snapshot = self.orderbook.get_l2_snapshot()
                stats = self.orderbook.get_stats()
                perf = self.get_performance_metrics()
                await self.send_to_all(json.dumps(l2_snapshot))
                await self.send_to_all(json.dumps(stats))
                await self.send_to_all(json.dumps(perf))
                
            elif data.get('type') == 'submit_order':
                # Track latency
                process_start = time.perf_counter()
                
                result = self.orderbook.submit_order(
                    data.get('side', 'buy'),
                    data.get('orderType', 'limit'),
                    data.get('price', 0),
                    data.get('quantity', 0)
                )
                
                # Calculate latency in microseconds
                process_latency = (time.perf_counter() - process_start) * 1_000_000
                self.latency_samples.append(process_latency)
                if len(self.latency_samples) > self.max_latency_samples:
                    self.latency_samples.pop(0)
                
                # Update performance metrics
                self.performance_metrics['orders_processed'] += 1
                self.performance_metrics['total_orders'] += 1
                if result.get('trades'):
                    self.performance_metrics['trades_executed'] += len(result.get('trades', []))
                    self.performance_metrics['total_trades'] += len(result.get('trades', []))
                
                # Send acknowledgment
                await websocket.send(json.dumps({
                    'type': 'order_ack',
                    'success': result['success'],
                    'orderId': result.get('order_id')
                }))
                
                # Always send order acknowledgment with order details for manual tracking
                order_details = {
                    'type': 'order_submitted',
                    'order_id': result.get('order_id'),
                    'side': data.get('side', 'buy'),
                    'orderType': data.get('orderType', 'limit'),
                    'price': data.get('price', 0),
                    'quantity': data.get('quantity', 0),
                    'timestamp': int(time.time() * 1000),
                    'manual': True,
                    'status': 'filled' if result.get('executed') else 'pending'
                }
                await websocket.send(json.dumps(order_details))
                
                # Broadcast trades immediately if any occurred (INSTANT FEEDBACK)
                if result.get('trades'):
                    for trade in result['trades']:
                        # Mark as manual trade (from user submission)
                        trade['manual'] = True
                        await self.send_to_all(json.dumps(trade))
                        print(f"  [TRADE] {trade['side'].upper()} {trade['quantity']} @ {trade['price']} (MANUAL)")
                    
                    # Update periodic trade count to avoid duplicates
                    if USE_CPP_ORDERBOOK and hasattr(self.orderbook, 'stats'):
                        self.last_periodic_trade_count = self.orderbook.stats.get_total_trades()
                
                # Broadcast updated market data (non-blocking)
                try:
                    l2_snapshot = self.orderbook.get_l2_snapshot()
                    stats = self.orderbook.get_stats()
                    
                    await self.send_to_all(json.dumps(l2_snapshot))
                    await self.send_to_all(json.dumps(stats))
                except Exception as e:
                    print(f"  [ERROR] Failed to broadcast market data: {e}")
                
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON received: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except KeyError as e:
            print(f"[ERROR] Missing required field: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Missing required field: {e}'
            }))
        except ValueError as e:
            print(f"[ERROR] Invalid value: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Invalid value: {e}'
            }))
        except Exception as e:
            print(f"[ERROR] Error processing message: {e}")
            import traceback
            traceback.print_exc()
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    def update_performance_metrics(self):
        """Update performance metrics calculations"""
        current_time = time.time()
        elapsed = current_time - self.performance_metrics['last_update_time']
        
        # Always calculate current rates (even if < 1 second, extrapolate)
        orders_this_period = self.performance_metrics['orders_processed']
        trades_this_period = self.performance_metrics['trades_executed']
        
        # Calculate rates - if elapsed is small, extrapolate to per-second
        if elapsed > 0:
            self.performance_metrics['orders_per_second'] = orders_this_period / elapsed
            self.performance_metrics['trades_per_second'] = trades_this_period / elapsed
        else:
            # If no time has passed, keep previous values or set to 0
            if orders_this_period == 0 and trades_this_period == 0:
                # Only set to 0 if we truly have no activity
                if elapsed > 2.0:  # After 2 seconds of no activity, show 0
                    self.performance_metrics['orders_per_second'] = 0.0
                    self.performance_metrics['trades_per_second'] = 0.0
        
        # Update peaks
        if self.performance_metrics['orders_per_second'] > self.performance_metrics['peak_orders_per_second']:
            self.performance_metrics['peak_orders_per_second'] = self.performance_metrics['orders_per_second']
        if self.performance_metrics['trades_per_second'] > self.performance_metrics['peak_trades_per_second']:
            self.performance_metrics['peak_trades_per_second'] = self.performance_metrics['trades_per_second']
        
        # Calculate average latency
        if self.latency_samples:
            self.performance_metrics['avg_latency_us'] = sum(self.latency_samples) / len(self.latency_samples)
        
        # Reset counters every second (but keep calculating rates continuously)
        if elapsed >= 1.0:
            self.performance_metrics['orders_processed'] = 0
            self.performance_metrics['trades_executed'] = 0
            self.performance_metrics['last_update_time'] = current_time
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        self.update_performance_metrics()
        uptime = time.time() - self.performance_metrics['start_time']
        metrics = {
            'type': 'performance',
            'orders_per_second': round(self.performance_metrics['orders_per_second'], 2),
            'trades_per_second': round(self.performance_metrics['trades_per_second'], 2),
            'avg_latency_us': round(self.performance_metrics['avg_latency_us'], 2),
            'peak_orders_per_second': round(self.performance_metrics['peak_orders_per_second'], 2),
            'peak_trades_per_second': round(self.performance_metrics['peak_trades_per_second'], 2),
            'total_orders': self.performance_metrics['total_orders'],
            'total_trades': self.performance_metrics['total_trades'],
            'uptime_seconds': round(uptime, 2)
        }
        return metrics
    
    async def auto_generate_orders(self):
        """Automatically generate orders to demonstrate system throughput"""
        base_price = 10000
        price_range = 50
        qty_range = (10, 500)
        
        while self.auto_generate_enabled:
            try:
                # Generate orders at specified rate (increased for more activity)
                orders_per_batch = max(10, self.auto_generate_rate // 5)  # Larger batches
                sleep_time = 0.05  # 50ms intervals for faster updates
                
                for _ in range(orders_per_batch):
                    # Alternate between buy and sell
                    side = random.choice(['buy', 'sell'])
                    price = base_price + random.randint(-price_range, price_range)
                    qty = random.randint(qty_range[0], qty_range[1])
                    
                    # Submit order (non-blocking)
                    process_start = time.perf_counter()
                    result = self.orderbook.submit_order(side, 'limit', price, qty)
                    process_latency = (time.perf_counter() - process_start) * 1_000_000
                    
                    # Update metrics
                    self.latency_samples.append(process_latency)
                    if len(self.latency_samples) > self.max_latency_samples:
                        self.latency_samples.pop(0)
                    
                    self.performance_metrics['orders_processed'] += 1
                    self.performance_metrics['total_orders'] += 1
                    
                    if result.get('trades'):
                        self.performance_metrics['trades_executed'] += len(result.get('trades', []))
                        self.performance_metrics['total_trades'] += len(result.get('trades', []))
                        
                        # Broadcast trades immediately
                        for trade in result['trades']:
                            await self.send_to_all(json.dumps(trade))
                
                await asyncio.sleep(sleep_time)
            except Exception as e:
                print(f"[ERROR] Auto-generate error: {e}")
                await asyncio.sleep(1)
    
    async def periodic_updates(self):
        """Send periodic market data updates and check for new trades"""
        while True:
            await asyncio.sleep(0.2)  # Update every 200ms for real-time feel
            
            if self.clients:
                # Check for new trades in real-time
                if USE_CPP_ORDERBOOK and hasattr(self.orderbook, 'stats'):
                    try:
                        current_trade_count = self.orderbook.stats.get_total_trades()
                        if current_trade_count > self.last_periodic_trade_count:
                            # New trades occurred
                            num_new_trades = current_trade_count - self.last_periodic_trade_count
                            recent_trades = self.orderbook.stats.get_recent_trades(num_new_trades)
                            
                            print(f"  [PERIODIC] Found {num_new_trades} new trade(s)")
                            
                            for trade in recent_trades:
                                trade_msg = {
                                    'type': 'trade',
                                    'price': trade.execution_price,
                                    'quantity': trade.execution_quantity,
                                    'side': 'buy' if trade.aggressor_side == lob_py.Side.BUY else 'sell',
                                    'timestamp': trade.timestamp
                                }
                                await self.send_to_all(json.dumps(trade_msg))
                                print(f"  [TRADE] {trade_msg['side'].upper()} {trade_msg['quantity']} @ {trade_msg['price']}")
                            
                            self.last_periodic_trade_count = current_trade_count
                    except Exception as e:
                        print(f"  [ERROR] Error checking for trades: {e}")
                
                # Send periodic L2, stats, and performance updates
                # This ensures UI updates continuously even with auto-generation
                l2_data = json.dumps(self.orderbook.get_l2_snapshot())
                stats_data = json.dumps(self.orderbook.get_stats())
                perf_metrics = self.get_performance_metrics()
                perf_data = json.dumps(perf_metrics)
                
                # Broadcast all updates
                await self.send_to_all(l2_data)
                await self.send_to_all(stats_data)
                await self.send_to_all(perf_data)


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
    
    # Wrapper function to handle websockets library API
    async def handler(websocket, path=None):
        await server.handle_client(websocket, path)
    
    # Start WebSocket server
    ws_server = await websockets.serve(
        handler,
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
    
    # Start auto-order generation for continuous activity
    print("  Starting auto-order generation (100 orders/sec)...")
    asyncio.create_task(server.auto_generate_orders())
    
    # Run forever
    await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[OK] Server stopped by user")
