cmake_minimum_required(VERSION 3.20)

# Find Python and pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Add pybind11 via submodule or FetchContent
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../include/lob/third_party/pybind11/CMakeLists.txt")
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../include/lob/third_party/pybind11 pybind11_build)
else()
    # Fallback to FetchContent
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.11.1
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# Create Python module
pybind11_add_module(lob_py bindings.cpp)

# Link against the C++ orderbook library
target_link_libraries(lob_py PRIVATE lob_core)

# Include directories
target_include_directories(lob_py PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

# Set output directory
set_target_properties(lob_py PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/python
    LIBRARY_OUTPUT_DIRECTORY_RELEASE ${CMAKE_BINARY_DIR}/python
    LIBRARY_OUTPUT_DIRECTORY_DEBUG ${CMAKE_BINARY_DIR}/python
)

# Install to build directory for easy import
install(TARGETS lob_py
    LIBRARY DESTINATION ${CMAKE_BINARY_DIR}/python
)
