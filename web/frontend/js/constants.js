/**
 * Application-wide constants
 * @fileoverview Centralized configuration for the orderbook frontend
 */

const CONFIG = {
    // WebSocket Configuration
    WS_URL: 'ws://localhost:8081',
    
    // UI Limits
    MAX_TRADES: 50,
    MAX_MANUAL_TRADES: 20,
    
    // Market Data
    BASE_PRICE: 10000,
    MOCK_UPDATE_INTERVAL: 2000, // milliseconds
    
    // Formatting
    PRICE_DECIMALS: 0,
    QUANTITY_DECIMALS: {
        M: 2,
        K: 1
    }
};

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}

