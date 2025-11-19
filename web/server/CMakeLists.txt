cmake_minimum_required(VERSION 3.20)

# WebSocket Server executable
add_executable(lob_server
    server_main.cpp
)

target_include_directories(lob_server PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)

target_link_libraries(lob_server PRIVATE
    lob_core
    ixwebsocket::ixwebsocket
    Threads::Threads
)

# Windows requires ws2_32 for Winsock (handled by ixwebsocket but good to be explicit if needed, though ixwebsocket handles its deps)
if(WIN32)
    target_link_libraries(lob_server PRIVATE ws2_32)
endif()

if(MSVC)
    target_compile_options(lob_server PRIVATE /W3)
else()
    target_compile_options(lob_server PRIVATE -Wno-deprecated-declarations)
endif()

message(STATUS "WebSocket server target: lob_server")
