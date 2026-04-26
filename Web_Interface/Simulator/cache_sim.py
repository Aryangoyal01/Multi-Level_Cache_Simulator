import math
from collections import defaultdict, deque

class CacheBlock:
    def __init__(self, block_addr, time, is_streaming=False):
        self.block_addr = block_addr
        self.insertion_time = time
        self.last_access_time = time
        self.is_streaming = is_streaming

class CacheLevel:
    def __init__(self, name, size, block_size, associativity, policy):
        self.name = name
        self.size = size
        self.block_size = block_size
        self.assoc = associativity
        self.policy = policy
        
        self.num_sets = size // (block_size * associativity)
        # Sets are dictionaries mapping: tag -> CacheBlock
        self.sets = [{} for _ in range(self.num_sets)]
        
        # Statistics
        self.accesses = 0
        self.hits = 0
        self.misses = 0

    def _get_set_and_tag(self, block_addr):
        set_idx = block_addr % self.num_sets
        tag = block_addr // self.num_sets
        return set_idx, tag

    def request(self, block_addr, time, future_map=None, is_streaming=False, record_stats=True):
        """Returns (hit_status, evicted_block_addr)"""
        if record_stats:
            self.accesses += 1

        set_idx, tag = self._get_set_and_tag(block_addr)
        cache_set = self.sets[set_idx]

        # Hit
        if tag in cache_set:
            if record_stats:
                self.hits += 1
            cache_set[tag].last_access_time = time
            cache_set[tag].is_streaming = is_streaming # Update metadata
            return True, None

        # Miss
        if record_stats:
            self.misses += 1
        
        evicted_addr = None
        # Need replacement?
        if len(cache_set) >= self.assoc:
            evicted_tag = self._find_victim(cache_set, time, future_map)
            evicted_addr = cache_set[evicted_tag].block_addr
            del cache_set[evicted_tag]

        # Insert new block
        cache_set[tag] = CacheBlock(block_addr, time, is_streaming)
        return False, evicted_addr

    def invalidate(self, block_addr):
        """Forces an eviction to maintain the inclusive property."""
        if block_addr is None:
            return
        set_idx, tag = self._get_set_and_tag(block_addr)
        if tag in self.sets[set_idx]:
            del self.sets[set_idx][tag]

    def _find_victim(self, cache_set, current_time, future_map):
        if self.policy == 'FIFO':
            return min(cache_set.keys(), key=lambda t: cache_set[t].insertion_time)
            
        elif self.policy == 'LRU':
            return min(cache_set.keys(), key=lambda t: cache_set[t].last_access_time)
            
        elif self.policy == 'BELADY':
            max_future_time = -1
            victim_tag = None
            for tag, block in cache_set.items():
                # future_map maps block_addr -> deque of access times
                futures = future_map.get(block.block_addr)
                next_access = futures[0] if futures else float('inf')
                if next_access > max_future_time:
                    max_future_time = next_access
                    victim_tag = tag
            return victim_tag
            
        elif self.policy == 'CUSTOM':
            # Goal: Evict streaming/stride blocks first to approximate reuse distance.
            # If multiple stream blocks exist, pick LRU among them. 
            # If no stream blocks exist, fallback to pure LRU.
            stream_blocks = {t: b for t, b in cache_set.items() if b.is_streaming}
            if stream_blocks:
                return min(stream_blocks.keys(), key=lambda t: stream_blocks[t].last_access_time)
            else:
                return min(cache_set.keys(), key=lambda t: cache_set[t].last_access_time)

class MultiLevelCacheSimulator:
    def __init__(self, configs, policy, warmup=50000):
        self.policy = policy
        self.warmup = warmup
        self.block_size = configs['block_size']
        
        self.l1 = CacheLevel('L1', configs['L1_size'], self.block_size, configs['L1_assoc'], policy)
        self.l2 = CacheLevel('L2', configs['L2_size'], self.block_size, configs['L2_assoc'], policy)
        self.l3 = CacheLevel('L3', configs['L3_size'], self.block_size, configs['L3_assoc'], policy)
        
        self.future_map = defaultdict(deque)
        self.stride_history = []
        self.current_time = 0

    def preprocess_belady(self, trace):
        """O(N) preprocessing to build a lookahead map for Belady's."""
        if self.policy != 'BELADY':
            return
        for time, addr in enumerate(trace):
            block_addr = addr // self.block_size
            self.future_map[block_addr].append(time)

    def process_trace(self, trace):
        self.preprocess_belady(trace)
        
        for time, addr in enumerate(trace):
            self.current_time = time
            block_addr = addr // self.block_size
            
            # Pop the current access from future_map to maintain lookahead accuracy
            if self.policy == 'BELADY' and self.future_map[block_addr]:
                self.future_map[block_addr].popleft()

            # Custom Policy: Stride Detection
            is_streaming = False
            if self.policy == 'CUSTOM':
                self.stride_history.append(block_addr)
                if len(self.stride_history) > 3:
                    self.stride_history.pop(0)
                if len(self.stride_history) == 3:
                    diff1 = self.stride_history[1] - self.stride_history[0]
                    diff2 = self.stride_history[2] - self.stride_history[1]
                    if diff1 == diff2 and diff1 != 0:
                        is_streaming = True

            record_stats = (time >= self.warmup)

            # --- Hierarchy Resolution (Inclusive) ---
            # 1. Access L1
            l1_hit, l1_evict = self.l1.request(block_addr, time, self.future_map, is_streaming, record_stats)
            if l1_hit: continue
            
            # 2. Access L2 (on L1 miss)
            l2_hit, l2_evict = self.l2.request(block_addr, time, self.future_map, is_streaming, record_stats)
            if l2_evict is not None:
                self.l1.invalidate(l2_evict) # Maintain inclusion
            if l2_hit: continue
            
            # 3. Access L3 (on L2 miss)
            l3_hit, l3_evict = self.l3.request(block_addr, time, self.future_map, is_streaming, record_stats)
            if l3_evict is not None:
                self.l2.invalidate(l3_evict) # Maintain inclusion
                self.l1.invalidate(l3_evict) # Maintain inclusion

def parse_trace(raw: str) -> list[int]:
    trace = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        _, addr = parts
        try:
            if addr.startswith("0x") or addr.startswith("0X"):
                trace.append(int(addr, 16))
            else:
                trace.append(int(addr))
        except:
            continue
    return trace


def run_simulation(trace: list[int], config: dict) -> dict:
    results = {}

    for policy in ["FIFO", "LRU", "BELADY", "CUSTOM"]:
        sim = MultiLevelCacheSimulator(config, policy)
        sim.process_trace(trace)

        results[policy] = {
            "L1": {
    "accesses": sim.l1.accesses,
    "hits": sim.l1.hits,
    "misses": sim.l1.misses,
    "hit_rate": (sim.l1.hits / sim.l1.accesses * 100) if sim.l1.accesses else 0,
    "miss_rate":(sim.l1.misses / sim.l1.accesses * 100)if sim.l1.accesses else 0,
},
"L2": {
    "accesses": sim.l2.accesses,
    "hits": sim.l2.hits,
    "misses": sim.l2.misses,
    "hit_rate": (sim.l2.hits / sim.l2.accesses * 100) if sim.l2.accesses else 0,
    "miss_rate":(sim.l2.misses / sim.l2.accesses * 100) if sim.l2.accesses else 0,
},
"L3": {
    "accesses": sim.l3.accesses,
    "hits": sim.l3.hits,
    "misses": sim.l3.misses,
    "hit_rate": (sim.l3.hits / sim.l3.accesses * 100) if sim.l3.accesses else 0,
    "miss_rate":(sim.l3.misses / sim.l3.accesses * 100) if sim.l3.accesses else 0,
},
        }

    return results
                