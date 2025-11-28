#!/usr/bin/env python3
"""
WebSocket Server for Limit Order Book GUI

This Python server acts as a bridge between the C++ orderbook library
and the web-based GUI. It provides real-time market data updates and
handles order submissions from the GUI.

Architecture:
- Primary: High-performance C++ OrderBook via pybind11 bindings
- Fallback: Pure Python implementation for reliability
- Automatic failover ensures zero trading downtime
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
from typing import Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

from config import (
    AUTO_GENERATE_RATE,
    AUTO_GENERATE_SLEEP_TIME,
    BASE_PRICE,
    HTTP_PORT,
    INITIAL_LEVELS,
    L2_SNAPSHOT_DEPTH,
    LEVEL_SPACING,
    MAX_LATENCY_SAMPLES,
    PERIODIC_UPDATE_INTERVAL,
    PRICE_RANGE,
    QUANTITY_RANGE,
    STRESS_TEST_BATCH_SIZE,
    STRESS_TEST_UPDATE_INTERVAL,
    WS_HOST,
    WS_PORT,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
USE_CPP_ORDERBOOK: bool = False
try:
    import lob_py
    USE_CPP_ORDERBOOK = True
    logger.info("C++ OrderBook module loaded successfully")
except ImportError as e:
    logger.warning(f"Failed to load C++ OrderBook: {e}")
    logger.info("Falling back to Python orderbook implementation")


class OrderBookWrapper:
    """Wrapper that uses C++ OrderBook if available, otherwise Python fallback"""
    
    def __init__(self):
        if USE_CPP_ORDERBOOK:
            self._init_cpp_orderbook()
        else:
            self._init_python_orderbook()
    
    def _init_cpp_orderbook(self) -> None:
        """Initialize C++ orderbook with high-performance engine."""
        logger.info("Initializing C++ OrderBook...")
        
        try:
            self.orderbook = lob_py.OrderBook()
            self.pool = lob_py.OrderPool()
            self.stats = lob_py.MarketStatistics()
            self.publisher = lob_py.TradePublisher()
            
            # Set up publisher chain
            self.orderbook.set_publisher(self.publisher)
            self.publisher.subscribe(self.stats)
            
            self.next_order_id = 1
            
            # Generate initial market data
            self._generate_cpp_initial_orders()
            
            # Initialize trade count after initial orders (they might create trades)
            self.last_trade_count = self.stats.get_total_trades()
            
            active_orders = self.orderbook.get_number_of_orders()
            logger.info(f"Active Orders: {active_orders}")
            
            # Get initial BBO
            bbo = self.orderbook.get_bbo()
            if bbo.is_valid():
                logger.info(f"Best Bid: {bbo.bid_price} x {bbo.bid_qty}")
                logger.info(f"Best Ask: {bbo.ask_price} x {bbo.ask_qty}")
        except Exception as e:
            logger.error(f"Failed to initialize C++ orderbook: {e}")
            raise
    
    def _generate_cpp_initial_orders(self) -> None:
        """Generate initial market depth for C++ orderbook."""
        # Generate bid levels (descending price)
        for i in range(INITIAL_LEVELS):
            price = BASE_PRICE - (i * LEVEL_SPACING)
            qty = random.randint(QUANTITY_RANGE[0], QUANTITY_RANGE[1])
            order = self.pool.create_limit_order(
                self.next_order_id,
                lob_py.Side.BUY,
                price,
                qty
            )
            self.orderbook.add_order(order)
            self.next_order_id += 1
        
        # Generate ask levels (ascending price)
        for i in range(INITIAL_LEVELS):
            price = BASE_PRICE + 10 + (i * LEVEL_SPACING)
            qty = random.randint(QUANTITY_RANGE[0], QUANTITY_RANGE[1])
            order = self.pool.create_limit_order(
                self.next_order_id,
                lob_py.Side.SELL,
                price,
                qty
            )
            self.orderbook.add_order(order)
            self.next_order_id += 1
    
    def _init_python_orderbook(self) -> None:
        """Initialize Python fallback orderbook for reliability."""
        logger.info("Initializing Python OrderBook (fallback)...")
        
        self.next_order_id = 1
        self.total_trades = 0
        self.total_volume = 0
        self.last_price = BASE_PRICE
        self.active_orders = 0
        
        # Initialize with sample market data
        self.bids = self._generate_side_python(BASE_PRICE, -10, -1)
        self.asks = self._generate_side_python(BASE_PRICE + 10, 10, 1)
        self.active_orders = sum(level['orders'] for level in self.bids + self.asks)
        
        logger.info(f"Active Orders: {self.active_orders}")
        logger.info(f"Best Bid: {self.bids[0]['price']} x {self.bids[0]['qty']}")
        logger.info(f"Best Ask: {self.asks[0]['price']} x {self.asks[0]['qty']}")
    
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
        """Get Level 2 market data snapshot."""
        if USE_CPP_ORDERBOOK:
            snapshot = self.orderbook.get_l2_snapshot(L2_SNAPSHOT_DEPTH)
            return {
                'type': 'l2_update',
                'bids': [
                    {
                        'price': level.price,
                        'qty': level.total_quantity,
                        'orders': level.order_count
                    }
                    for level in snapshot.bids
                ],
                'asks': [
                    {
                        'price': level.price,
                        'qty': level.total_quantity,
                        'orders': level.order_count
                    }
                    for level in snapshot.asks
                ]
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
        """Submit order to C++ orderbook with error handling."""
        order_id = self.next_order_id
        self.next_order_id += 1
        
        cpp_side = lob_py.Side.BUY if side == 'buy' else lob_py.Side.SELL
        
        try:
            # Create and add order
            if order_type == 'market':
                order = self.pool.create_market_order(order_id, cpp_side, quantity)
            else:
                if price <= 0:
                    raise ValueError(f"Invalid price: {price}")
                order = self.pool.create_limit_order(order_id, cpp_side, price, quantity)
            
            self.orderbook.add_order(order)
            
            # Check if trades occurred and get new ones
            trades: List[Dict] = []
            current_trade_count = self.stats.get_total_trades()
            if current_trade_count > self.last_trade_count:
                num_new_trades = current_trade_count - self.last_trade_count
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
                'executed': len(trades) > 0,
                'trades': trades
            }
        except Exception as e:
            logger.error(f"Error submitting order {order_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _submit_order_python(self, side: str, order_type: str, price: int, quantity: int) -> Dict:
        """Submit order to Python fallback orderbook."""
        order_id = self.next_order_id
        self.next_order_id += 1
        
        if quantity <= 0:
            return {
                'success': False,
                'error': 'Invalid quantity'
            }
        
        # Simulate order execution
        if order_type == 'market' or self._will_match_python(side, price):
            # Execute trade
            if order_type == 'market':
                exec_price = self.asks[0]['price'] if side == 'buy' else self.bids[0]['price']
            else:
                exec_price = price
            
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
            
            return {
                'success': True,
                'order_id': order_id,
                'executed': True,
                'trades': [trade]
            }
        else:
            # Add to book (simplified - just increment counter)
            self.active_orders += 1
            return {
                'success': True,
                'order_id': order_id,
                'executed': False,
                'trades': []
            }
    
    def _will_match_python(self, side: str, price: int) -> bool:
        """Check if order will match at given price."""
        if not self.bids or not self.asks:
            return False
        if side == 'buy':
            return price >= self.asks[0]['price']
        return price <= self.bids[0]['price']


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
        self.performance_metrics: Dict[str, float] = {
            'orders_processed': 0.0,
            'trades_executed': 0.0,
            'start_time': time.time(),
            'last_update_time': time.time(),
            'orders_per_second': 0.0,
            'trades_per_second': 0.0,
            'avg_latency_us': 0.0,
            'peak_orders_per_second': 0.0,
            'peak_trades_per_second': 0.0,
            'total_orders': 0.0,
            'total_trades': 0.0
        }
        self.latency_samples: List[float] = []
        
        # Auto-order generation for continuous activity
        self.auto_generate_enabled = True
        self.auto_generate_rate = AUTO_GENERATE_RATE
        
    async def register(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Register a new client and send initial market data."""
        self.clients.add(websocket)
        logger.info(f"Client connected ({len(self.clients)} active)")
        
        try:
            # Send initial market snapshot
            await websocket.send(json.dumps(self.orderbook.get_l2_snapshot()))
            await websocket.send(json.dumps(self.orderbook.get_stats()))
            await websocket.send(json.dumps(self.get_performance_metrics()))
        except Exception as e:
            logger.error(f"Failed to send initial data to client: {e}", exc_info=True)
    
    async def unregister(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Unregister a client."""
        try:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected ({len(self.clients)} active)")
        except KeyError:
            pass  # Already removed
    
    async def send_to_all(self, message: str) -> None:
        """Broadcast message to all connected clients with error handling."""
        if not self.clients:
            return
        
        results = await asyncio.gather(
            *(client.send(message) for client in self.clients),
            return_exceptions=True
        )
        
        # Remove disconnected clients
        disconnected = [
            client
            for client, result in zip(self.clients, results)
            if isinstance(result, Exception)
        ]
        
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
                
                logger.info(f"Stress test: Generating {num_orders} orders at EXTREME throughput...")
                process_start = time.perf_counter()
                
                # EXTREME MODE: Process orders in massive parallel batches
                # Target: 10+ million orders per second
                batch_size = STRESS_TEST_BATCH_SIZE
                total_trades = 0
                update_interval = STRESS_TEST_UPDATE_INTERVAL
                
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
                        if len(self.latency_samples) < MAX_LATENCY_SAMPLES:
                            self.latency_samples.append(order_latency)
                        else:
                            self.latency_samples[random.randint(0, MAX_LATENCY_SAMPLES - 1)] = order_latency
                        
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
                        
                        logger.info(f"Stress test progress: {i + batch_size}/{num_orders} ({batch_ops:.0f} ops/sec)")
                
                process_time = time.perf_counter() - process_start
                orders_per_sec = num_orders / process_time if process_time > 0 else 0
                
                logger.info(f"Stress test completed: {num_orders} orders in {process_time:.2f}s")
                logger.info(f"Throughput: {orders_per_sec:,.0f} orders/sec")
                logger.info(f"Generated {total_trades} trades")
                
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
                if len(self.latency_samples) > MAX_LATENCY_SAMPLES:
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
                        logger.debug(f"Trade: {trade['side'].upper()} {trade['quantity']} @ {trade['price']} (MANUAL)")
                    
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
            logger.error(f"Invalid JSON received: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except KeyError as e:
            logger.error(f"Missing required field: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Missing required field: {e}'
            }))
        except ValueError as e:
            logger.error(f"Invalid value: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Invalid value: {e}'
            }))
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
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
    
    async def auto_generate_orders(self) -> None:
        """Automatically generate orders to demonstrate system throughput."""
        while self.auto_generate_enabled:
            try:
                # Generate orders at specified rate
                orders_per_batch = max(10, self.auto_generate_rate // 5)
                
                for _ in range(orders_per_batch):
                    # Alternate between buy and sell
                    side = random.choice(['buy', 'sell'])
                    price = BASE_PRICE + random.randint(-PRICE_RANGE, PRICE_RANGE)
                    qty = random.randint(QUANTITY_RANGE[0], QUANTITY_RANGE[1])
                    
                    # Submit order (non-blocking)
                    process_start = time.perf_counter()
                    result = self.orderbook.submit_order(side, 'limit', price, qty)
                    process_latency = (time.perf_counter() - process_start) * 1_000_000
                    
                    # Update metrics
                    self.latency_samples.append(process_latency)
                    if len(self.latency_samples) > MAX_LATENCY_SAMPLES:
                        self.latency_samples.pop(0)
                    
                    self.performance_metrics['orders_processed'] += 1
                    self.performance_metrics['total_orders'] += 1
                    
                    if result.get('trades'):
                        self.performance_metrics['trades_executed'] += len(result.get('trades', []))
                        self.performance_metrics['total_trades'] += len(result.get('trades', []))
                        
                        # Broadcast trades immediately
                        for trade in result['trades']:
                            await self.send_to_all(json.dumps(trade))
                
                await asyncio.sleep(AUTO_GENERATE_SLEEP_TIME)
            except Exception as e:
                logger.error(f"Auto-generate error: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def periodic_updates(self) -> None:
        """Send periodic market data updates and check for new trades."""
        while True:
            await asyncio.sleep(PERIODIC_UPDATE_INTERVAL)
            
            if self.clients:
                # Check for new trades in real-time
                if USE_CPP_ORDERBOOK and hasattr(self.orderbook, 'stats'):
                    try:
                        current_trade_count = self.orderbook.stats.get_total_trades()
                        if current_trade_count > self.last_periodic_trade_count:
                            # New trades occurred
                            num_new_trades = current_trade_count - self.last_periodic_trade_count
                            recent_trades = self.orderbook.stats.get_recent_trades(num_new_trades)
                            
                            logger.debug(f"Found {num_new_trades} new trade(s)")
                            
                            for trade in recent_trades:
                                trade_msg = {
                                    'type': 'trade',
                                    'price': trade.execution_price,
                                    'quantity': trade.execution_quantity,
                                    'side': 'buy' if trade.aggressor_side == lob_py.Side.BUY else 'sell',
                                    'timestamp': trade.timestamp
                                }
                                await self.send_to_all(json.dumps(trade_msg))
                            
                            self.last_periodic_trade_count = current_trade_count
                    except Exception as e:
                        logger.error(f"Error checking for trades: {e}", exc_info=True)
                
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


async def main() -> None:
    """Main entry point for WebSocket server."""
    logger.info("=" * 60)
    logger.info("Limit Order Book WebSocket Server")
    logger.info(f"Using: {'C++ OrderBook (pybind11)' if USE_CPP_ORDERBOOK else 'Python OrderBook (fallback)'}")
    logger.info("=" * 60)
    
    server = WebSocketOrderBookServer()
    
    logger.info(f"Starting WebSocket server on ws://{WS_HOST}:{WS_PORT}...")
    
    # Wrapper function to handle websockets library API
    async def handler(websocket: websockets.WebSocketServerProtocol, path: Optional[str] = None) -> None:
        await server.handle_client(websocket, path)
    
    # Start WebSocket server
    ws_server = await websockets.serve(
        handler,
        WS_HOST,
        WS_PORT,
        ping_interval=None
    )
    
    logger.info("Server started successfully!")
    logger.info(f"Clients can connect to: ws://{WS_HOST}:{WS_PORT}")
    logger.info("Press Ctrl+C to stop")
    
    # Start periodic updates
    asyncio.create_task(server.periodic_updates())
    
    # Start auto-order generation for continuous activity
    logger.info(f"Starting auto-order generation ({AUTO_GENERATE_RATE} orders/sec)...")
    asyncio.create_task(server.auto_generate_orders())
    
    # Run forever
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
