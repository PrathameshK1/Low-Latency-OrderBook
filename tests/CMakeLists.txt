# Tests placeholder
add_executable(test_memory_pool
    unit/test_memory_pool.cpp
)
target_link_libraries(test_memory_pool PRIVATE lob_core)
add_test(NAME MemoryPoolTest COMMAND test_memory_pool)
