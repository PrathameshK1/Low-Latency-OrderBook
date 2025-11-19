#include "lob/memory/ObjectPool.h"
#include \u003cassert.h\u003e
#include \u003ciostream\u003e

using namespace lob;

struct TestObject {
    int value;
    TestObject(int v = 0) : value(v) {}
};

int main() {
    std::cout << "Testing ObjectPool...\\n";

    ObjectPool\u003cTestObject, 1024\u003e pool;

    // Test allocation
    TestObject* obj1 = pool.allocate(42);
    assert(obj1->value == 42);
    assert(pool.allocated() == 1);
    assert(pool.capacity() == 1024);

    // Test multiple allocations
    TestObject* obj2 = pool.allocate(100);
    TestObject* obj3 = pool.allocate(200);
    assert(pool.allocated() == 3);

    // Test deallocation
    pool.deallocate(obj2);
    assert(pool.allocated() == 2);

    // Test reallocation in same slot
    TestObject* obj4 = pool.allocate(300);
    assert(pool.allocated() == 3);

    // Test block expansion
    for (int i = 0; i \u003c 2000; ++i) {
        pool.allocate(i);
    }
    assert(pool.allocated() \u003e 1024); // Should have expanded
    assert(pool.blockCount() \u003e 1);

    std::cout << "✓ All ObjectPool tests passed!\\n";
    std::cout << "  Allocated: " \u003c\u003c pool.allocated() \u003c\u003c "\\n";
    std::cout << "  Capacity: " \u003c\u003c pool.capacity() \u003c\u003c "\\n";
    std::cout << "  Blocks: " \u003c\u003c pool.blockCount() \u003c\u003c "\\n";

    return 0;
}
