# Start Order Book System

## Quick Start Guide

This guide will help you start the system with the high-performance C++ OrderBook backend.

### Step 1: Start WebSocket Server (Port 8081)

This server uses the C++ OrderBook via pybind11 bindings.

Open a terminal and run:

```powershell
cd c:\Users\HP\Desktop\Limit-Order-Book
python web\server\websocket_server.py
```

You should see:
```
============================================================
  Limit Order Book WebSocket Server
  Using: C++ OrderBook (pybind11)
============================================================
[OK] C++ OrderBook module loaded successfully!
Initializing C++ OrderBook...
  Active Orders: 20
  Best Bid: 9955 x 300
  Best Ask: 10055 x 300
[OK] Server started successfully!
```

### Step 2: Start HTTP Server for GUI (Port 8082)

Open a **NEW terminal** and run:

```powershell
cd c:\Users\HP\Desktop\Limit-Order-Book  
python web\serve_gui.py
```

You should see:
```
============================================================
  Order Book GUI Server
============================================================
  Serving at: http://localhost:8082
  Press Ctrl+C to stop
============================================================
```

### Step 3: Open the GUI

Open your browser and navigate to:
```
http://localhost:8082
```

### Troubleshooting

**Port already in use?**
- Kill existing processes: `netstat -ano | findstr :8081` then `taskkill /PID <pid> /F`

**"DLL load failed" error?**
- The server will automatically fall back to the Python implementation.
- To fix, ensure the required DLLs (`libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll`) are in `web/server/`.

**Rebuilding the C++ Module**
If you need to rebuild the bindings:
```powershell
# Add MinGW to PATH
$env:PATH = "C:\ProgramData\mingw64\mingw64\bin;" + $env:PATH

# Build
cmake -G "MinGW Makefiles" -B build -S . -DPython3_EXECUTABLE="C:\Python312\python.exe" -DBUILD_PYTHON_BINDINGS=ON
cmake --build build --target lob_py --config Release

# Deploy
copy build\python\lob_py.cp312-win_amd64.pyd web\server\lob_py.pyd
```
