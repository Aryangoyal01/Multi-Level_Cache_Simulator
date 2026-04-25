#include <cstdint>
#include <iostream>
#include <vector>
#include <random>

// L1 Cache is 32KB.
// The Pattern array is 16KB (2048 * 8 bytes). It fits easily in L1.
const size_t PATTERN_ELEMENTS = 2048; 

// The Noise array is 256KB (32768 * 8 bytes). It will flood the L1 cache.
const size_t NOISE_ELEMENTS = 32768;  

static uint64_t TraceWorkload() {
    std::vector<uint64_t> pattern_data(PATTERN_ELEMENTS, 1);
    std::vector<uint64_t> noise_data(NOISE_ELEMENTS, 1);
    uint64_t sum = 0;

    // Fixed seed so your Intel Pin traces are deterministic and perfectly repeatable
    std::mt19937 rng(42); 
    std::uniform_int_distribution<size_t> dist(0, NOISE_ELEMENTS - 1);

    std::cout << "Executing memory accesses...\n";

    // Loop enough times to easily clear your 50,000 line cache warmup
    // This will generate roughly 300,000 to 500,000 memory accesses depending on compiler optimizations
    for (int i = 0; i < 15000; ++i) {
        
        // PHASE A: The Predictable Stride (SRD thrives here)
        // We sequentially read through the pattern array. 
        for (int j = 0; j < 16; ++j) {
            size_t pattern_idx = ((i * 16) + j) % PATTERN_ELEMENTS;
            sum += pattern_data[pattern_idx];
        }

        // PHASE B: The Cache Thrashing Noise (LRU dies here)
        // We jump around the 256KB array completely at random.
        // Under LRU, these random blocks will evict our nice pattern array.
        for (int j = 0; j < 16; ++j) {
            size_t noise_idx = dist(rng);
            noise_data[noise_idx] += 1; // Read and Write
            sum ^= noise_data[noise_idx];
        }
    }

    return sum;
}

int main() {
    std::cout << "Starting LRU vs SRD cache stress test...\n";
    uint64_t result = TraceWorkload();
    std::cout << "Done. Integrity check result = " << result << "\n";
    return 0;
}