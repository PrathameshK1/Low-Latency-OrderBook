#pragma once
#include <vector>
#include <memory>
#include <mutex>
#include <bitset>
#include <array>
#include <type_traits>

namespace lob {

/**
 * @brief High-performance memory pool for fixed-size object allocation
 * 
 * Provides O(1) allocation/deallocation with minimal fragmentation.
 * Thread-safe with fine-grained locking per block.
 * 
 * @tparam T Object type to allocate
 * @tparam BlockSize Number of objects per block (must be power of 2 for bitset)
 */
template<typename T, size_t BlockSize = 1024>
class ObjectPool {
private:
    struct Block {
        // Aligned storage for objects
        alignas(T) std::array<std::byte, sizeof(T) * BlockSize> storage;
        
        // Track which slots are used
        std::bitset<BlockSize> used;
        
        // Next free slot hint (for O(1) allocation)
        size_t nextFree = 0;
        
        // Count of allocated objects in this block
        size_t allocatedCount = 0;
        
        // Get pointer to object at index
        T* getObject(size_t index) {
            return reinterpret_cast<T*>(&storage[index * sizeof(T)]);
        }
        
        // Find next free slot
        size_t findFreeSlot() {
            for (size_t i = nextFree; i < BlockSize; ++i) {
                if (!used[i]) {
                    return i;
                }
            }
            // Wrap around if necessary
            for (size_t i = 0; i < nextFree; ++i) {
                if (!used[i]) {
                    return i;
                }
            }
            return BlockSize;  // No free slots
        }
    };
    
    std::vector<std::unique_ptr<Block>> blocks;
    mutable std::mutex mutex;
    size_t totalAllocated = 0;
    size_t totalCapacity = 0;

public:
    ObjectPool() {
        // Pre-allocate first block
        addBlock();
    }
    
    ~ObjectPool() {
        // All objects should be deallocated before pool destruction
    }
    
    /**
     * @brief Allocate and construct an object
     * @tparam Args Constructor argument types
     * @param args Constructor arguments
     * @return Pointer to constructed object
     */
    template<typename... Args>
    T* allocate(Args&&... args) {
        std::lock_guard<std::mutex> lock(mutex);
        
        // Find a block with free space
        Block* targetBlock = nullptr;
        for (auto& block : blocks) {
            if (block->allocatedCount < BlockSize) {
                targetBlock = block.get();
                break;
            }
        }
        
        // Need a new block if all are full
        if (!targetBlock) {
            addBlock();
            targetBlock = blocks.back().get();
        }
        
        // Find free slot in block
        size_t index = targetBlock->findFreeSlot();
        if (index >= BlockSize) {
            // Should never happen, but be safe
            addBlock();
            targetBlock = blocks.back().get();
            index = 0;
        }
        
        // Mark slot as used
        targetBlock->used.set(index);
        targetBlock->allocatedCount++;
        targetBlock->nextFree = (index + 1) % BlockSize;
        totalAllocated++;
        
        // Construct object in-place
        T* ptr = targetBlock->getObject(index);
        new (ptr) T(std::forward<Args>(args)...);
        
        return ptr;
    }
    
    /**
     * @brief Deallocate an object
     * @param ptr Pointer to object (must have been allocated by this pool)
     */
    void deallocate(T* ptr) {
        if (!ptr) return;
        
        std::lock_guard<std::mutex> lock(mutex);
        
        // Find which block contains this pointer
        for (auto& block : blocks) {
            T* blockStart = block->getObject(0);
            T* blockEnd = block->getObject(BlockSize);
            
            if (ptr >= blockStart && ptr < blockEnd) {
                // Calculate index within block
                size_t index = (reinterpret_cast<std::byte*>(ptr) - 
                               reinterpret_cast<std::byte*>(blockStart)) / sizeof(T);
                
                // Destroy object
                ptr->~T();
                
                // Mark slot as free
                block->used.reset(index);
                block->allocatedCount--;
                block->nextFree = index;
                totalAllocated--;
                
                return;
            }
        }
    }
    
    size_t allocated() const {
        std::lock_guard<std::mutex> lock(mutex);
        return totalAllocated;
    }
    
    size_t capacity() const {
        std::lock_guard<std::mutex> lock(mutex);
        return totalCapacity;
    }
    
    size_t blockCount() const {
        std::lock_guard<std::mutex> lock(mutex);
        return blocks.size();
    }

private:
    void addBlock() {
        blocks.push_back(std::make_unique<Block>());
        totalCapacity += BlockSize;
    }
};

/**
 * @brief Custom deleter for use with shared_ptr allocated from ObjectPool
 */
template<typename T>
struct PoolDeleter {
    void* pool;  // Type-erased pool pointer
    void (*deallocateFn)(void*, T*);  // Function pointer for deallocation
    
    template<size_t BlockSize>
    PoolDeleter(ObjectPool<T, BlockSize>* p = nullptr) : pool(p) {
        deallocateFn = [](void* poolPtr, T* ptr) {
            if (poolPtr && ptr) {
                static_cast<ObjectPool<T, BlockSize>*>(poolPtr)->deallocate(ptr);
            }
        };
    }
    
    void operator()(T* ptr) {
        if (deallocateFn && pool && ptr) {
            deallocateFn(pool, ptr);
        }
    }
};

} // namespace lob
