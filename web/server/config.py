"""
Configuration constants for the OrderBook WebSocket server.
"""
from typing import Final

# Server Configuration
WS_HOST: Final[str] = "localhost"
WS_PORT: Final[int] = 8081
HTTP_PORT: Final[int] = 8082

# Performance Configuration
AUTO_GENERATE_RATE: Final[int] = 100  # Orders per second
MAX_LATENCY_SAMPLES: Final[int] = 1000
PERIODIC_UPDATE_INTERVAL: Final[float] = 0.2  # seconds
AUTO_GENERATE_SLEEP_TIME: Final[float] = 0.05  # seconds

# Stress Test Configuration
STRESS_TEST_BATCH_SIZE: Final[int] = 10000
STRESS_TEST_UPDATE_INTERVAL: Final[int] = 10000

# Market Data Configuration
BASE_PRICE: Final[int] = 10000
PRICE_RANGE: Final[int] = 50
QUANTITY_RANGE: Final[tuple[int, int]] = (10, 1000)
INITIAL_LEVELS: Final[int] = 10
LEVEL_SPACING: Final[int] = 5

# Order Book Configuration
L2_SNAPSHOT_DEPTH: Final[int] = 10

