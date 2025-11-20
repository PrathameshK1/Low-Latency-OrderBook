# Low-Latency Limit Order Book (Hybrid C++/Python)

A state-of-the-art, high-frequency trading (HFT) limit order book implementation that combines the raw performance of C++20 with the flexibility of Python.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![C++](https://img.shields.io/badge/C++-20-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-yellow.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)

## 🚀 Overview

This project demonstrates a production-grade trading system architecture. It uses a **C++20 matching engine** for sub-microsecond order execution, exposed to a **Python WebSocket server** via **pybind11** bindings. This allows for high-performance core logic while maintaining easy integration with web frontends and data analysis tools.

### Key Features

*   **⚡ Ultra-Low Latency**: Core matching engine written in optimized C++20.
*   **🧠 Hybrid Architecture**: Seamless C++ integration with Python using `pybind11`.
*   **🌊 Zero-Allocation**: Custom memory pools (`ObjectPool`) to eliminate runtime heap allocation.
*   **📊 Real-Time Visualization**: Modern glassmorphism Web GUI with live L2 depth and trade feed.
*   **🛡️ Robust Design**: Price-time priority matching, O(1) lookups, and thread-safe architecture.

---

## 🏗️ System Architecture

The system follows a layered architecture designed for performance and scalability:

```mermaid
graph TD
    User[Web Browser / Trader] <-->|WebSocket (JSON)| PyServer[Python WebSocket Server]
    User <-->|HTTP| WebServer[GUI Server]
    
    subgraph "Backend Core (Hybrid)"
        PyServer <-->|pybind11| Bindings[C++ Bindings (lob_py)]
        Bindings <-->|Direct Call| Engine[C++ Matching Engine]
        Engine <-->|O(1)| Memory[Memory Pools]
    end
```

### 1. C++ Core (`src/core/`)
The heart of the system. Handles order matching, book management, and market data generation.
*   **`OrderBook`**: Manages Bids/Asks using `std::map` and `std::unordered_map` for fast lookups.
*   **`OrderPool`**: Pre-allocated memory blocks to prevent memory fragmentation and GC pauses.

### 2. Python Bindings (`bindings/`)
Uses `pybind11` to expose C++ classes (`OrderBook`, `Order`, `L2Snapshot`) as a native Python module (`lob_py`). This allows Python to directly manipulate C++ objects with near-zero overhead.

### 3. Python Server (`web/server/`)
A `asyncio` WebSocket server that:
*   Loads the high-performance C++ module.
*   Handles client connections.
*   Broadcasts market data updates.
*   **Fallback Mechanism**: Automatically switches to a pure Python implementation if the C++ module fails to load.

### 4. Web Frontend (`web/frontend/`)
A professional trading terminal interface:
*   **Tech Stack**: Vanilla JS, CSS3 (Glassmorphism), HTML5.
*   **Features**: Dynamic depth chart, real-time ticker, one-click order entry.

---

## 🛠️ Prerequisites

*   **OS**: Windows (tested on Windows 10/11), Linux, or macOS.
*   **Compiler**: GCC 10+ (MinGW-w64 on Windows) or Clang 12+.
*   **CMake**: Version 3.20 or higher.
*   **Python**: Version 3.12+ (Must match the architecture of your compiler, e.g., 64-bit).
*   **Dependencies**:
    *   `pip install pybind11 websockets`

---

## 📦 Build & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/Limit-Order-Book.git
cd Limit-Order-Book
```

### 2. Build the C++ Module
We use CMake to build the `lob_py` Python extension.

**Windows (PowerShell):**
```powershell
# Add MinGW to PATH (if not already)
$env:PATH = "C:\ProgramData\mingw64\mingw64\bin;" + $env:PATH

# Configure CMake (Force Python 3.12)
cmake -G "MinGW Makefiles" -B build -S . -DPython3_EXECUTABLE="C:\Python312\python.exe" -DBUILD_PYTHON_BINDINGS=ON

# Build the module
cmake --build build --target lob_py --config Release
```

### 3. Deploy the Module
Copy the built extension and required DLLs to the server directory.

```powershell
# Copy Python Extension
copy build\python\lob_py.cp312-win_amd64.pyd web\server\lob_py.pyd

# Copy Runtime DLLs (Required for MinGW)
copy C:\ProgramData\mingw64\mingw64\bin\libgcc_s_seh-1.dll web\server\
copy C:\ProgramData\mingw64\mingw64\bin\libstdc++-6.dll web\server\
copy C:\ProgramData\mingw64\mingw64\bin\libwinpthread-1.dll web\server\
```

---

## 🚀 Running the System

### Step 1: Start the WebSocket Server
This starts the backend. It will load the C++ module and listen for connections.

```powershell
python web/server/websocket_server.py
```
*Expected Output:*
```
[OK] C++ OrderBook module loaded successfully!
[OK] Server started successfully!
```

### Step 2: Start the GUI Server
Open a **new terminal** and run:

```powershell
python web/serve_gui.py
```

### Step 3: Access the Terminal
Open your browser and navigate to:
👉 **http://localhost:8082**

---

## 🔮 Future Roadmap

We are constantly pushing the boundaries of performance. Here is what's coming next:

*   **Pure C++ WebSocket Server**: Replace the Python server entirely with a C++ WebSocket implementation (using `uWebSockets` or `Boost.Beast`) to eliminate the Python GIL and achieve microsecond-level wire-to-wire latency.
*   **FIX Protocol Support**: Implement a FIX 4.2/5.0 engine for institutional connectivity.
*   **Market Data Replay**: Tools to replay historical PCAP data for backtesting strategies.
*   **FPGA Acceleration**: Explore HLS for offloading matching logic to hardware.

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
