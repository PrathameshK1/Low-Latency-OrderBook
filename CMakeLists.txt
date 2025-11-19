cmake_minimum_required(VERSION 3.20)
project(LimitOrderBook VERSION 1.0.0 LANGUAGES CXX)

# C++20 required
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler warnings and optimizations
if(MSVC)
    add_compile_options(/W4)
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        add_compile_options(/O2)
    endif()
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        add_compile_options(-O3)
    endif()
endif()

# Library: Core Orderbook
add_library(lob_core
    src/core/Order.cpp
    src/core/OrderBook.cpp
)

target_include_directories(lob_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Try to find dependencies (optional for now)
find_package(Threads REQUIRED)
target_link_libraries(lob_core PUBLIC Threads::Threads)

# Example: Demo GUI application (will add WebSocket server later)
add_executable(lob_demo
    examples/demo_basic.cpp
)

target_link_libraries(lob_demo PRIVATE lob_core)

# Tests (placeholder)
enable_testing()
add_subdirectory(tests EXCLUDE_FROM_ALL)

# Install rules
install(TARGETS lob_core
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(DIRECTORY include/lob
    DESTINATION include
)

message(STATUS "")
message(STATUS "=== Limit Order Book Configuration ===")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "=====================================")
message(STATUS "")
