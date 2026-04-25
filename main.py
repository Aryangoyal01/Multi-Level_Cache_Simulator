import matplotlib.pyplot as plt
import numpy as np
import os
from cache_sim import MultiLevelCacheSimulator

def load_trace(filepath):
    """Reads addresses from a file, handling prefixes like 'R' or 'W' from PIN traces."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Trace file not found: {filepath}")
    
    trace = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Split the line by spaces (e.g., 'W 0x7fffc6606f58' becomes ['W', '0x7fffc6606f58'])
            parts = line.split()
            
            # Look for the part of the line that represents the address
            addr_str = None
            for part in parts:
                if part.lower().startswith('0x') or part.isdigit():
                    addr_str = part
                    break
            
            if addr_str:
                try:
                    if 'x' in addr_str.lower():
                        trace.append(int(addr_str, 16))
                    else:
                        trace.append(int(addr_str))
                except ValueError:
                    # Safely skip lines that can't be parsed
                    continue
                    
    return trace

def is_power_of_two(n):
    return (n != 0) and (n & (n - 1) == 0)

def plot_results(results_dict):
    policies = list(results_dict.keys())
    levels = ['L1', 'L2', 'L3']
    
    hit_rates = {level: [results_dict[p][level]['hit_rate'] for p in policies] for level in levels}
    
    x = np.arange(len(policies))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width, hit_rates['L1'], width, label='L1 Hit Rate', color='#4C72B0')
    bars2 = ax.bar(x, hit_rates['L2'], width, label='L2 Hit Rate', color='#55A868')
    bars3 = ax.bar(x + width, hit_rates['L3'], width, label='L3 Hit Rate', color='#C44E52')

    ax.set_ylabel('Hit Rate (%)')
    ax.set_title('Cache Replacement Policy Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(policies)
    ax.legend()
    ax.set_ylim(0, 100)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig("policy_comparison.png", dpi=300)
    print("\nPlot saved as 'policy_comparison.png'")
    plt.show()

def get_valid_int(prompt, default, enforce_power_of_2=False):
    while True:
        user_input = input(f"{prompt} [Default: {default}]: ").strip()
        if not user_input:
            return default
        try:
            val = int(user_input)
            if val <= 0:
                print("  -> Value must be greater than 0. Try again.")
                continue
            if enforce_power_of_2 and not is_power_of_two(val):
                print("  -> Value must be a power of 2. Try again.")
                continue
            return val
        except ValueError:
            print("  -> Invalid input. Please enter an integer.")

def get_user_configs():
    """Prompts the user for cache configurations with validation."""
    print("--- Cache Configuration Setup ---")
    print("Press [Enter] to keep the default value for any setting.\n")

    while True:
        block_size = get_valid_int("Block Size in Bytes (Power of 2)", 64, enforce_power_of_2=True)
        
        l1_size = get_valid_int("L1 Cache Size in Bytes (Power of 2)", 32768, enforce_power_of_2=True)
        l1_assoc = get_valid_int("L1 Associativity (Power of 2)", 8, enforce_power_of_2=True)
        
        l2_size = get_valid_int("L2 Cache Size in Bytes (Power of 2)", 262144, enforce_power_of_2=True)
        l2_assoc = get_valid_int("L2 Associativity (Power of 2)", 8, enforce_power_of_2=True)
        
        l3_size = get_valid_int("L3 Cache Size in Bytes (Power of 2)", 2097152, enforce_power_of_2=True)
        l3_assoc = get_valid_int("L3 Associativity (Power of 2)", 16, enforce_power_of_2=True)

        # Validate that size is large enough for the blocks and associativity
        if (l1_size < block_size * l1_assoc) or \
           (l2_size < block_size * l2_assoc) or \
           (l3_size < block_size * l3_assoc):
            print("\n[!] Configuration Error: Cache size must be >= (Block Size * Associativity).")
            print("Please re-enter your configurations.\n")
            continue
        break

    configs = {
        'block_size': block_size,
        'L1_size': l1_size,
        'L1_assoc': l1_assoc,
        'L2_size': l2_size,
        'L2_assoc': l2_assoc,
        'L3_size': l3_size,
        'L3_assoc': l3_assoc
    }
    
    warmup_accesses = get_valid_int("\nWarmup Accesses to skip (Integer)", 50000, enforce_power_of_2=False)
    
    return configs, warmup_accesses

def main():
    # 1. Configuration Validation
    cache_configs, warmup_accesses = get_user_configs()
    
    # 2. Get Trace File
    while True:
        trace_path = input("\nEnter trace file path [Default: memory_trace.txt]: ").strip()
        if not trace_path:
            trace_path = "memory_trace.txt"
        
        try:
            print("Loading trace...")
            trace = load_trace(trace_path)
            print(f"Successfully loaded {len(trace)} memory accesses.")
            break
        except FileNotFoundError as e:
            print(f"Error: {e}. Please check the path and try again.")
    
    policies = ['FIFO', 'LRU', 'BELADY', 'CUSTOM']
    results = {}

    # 3. Run Simulations
    for policy in policies:
        print(f"\nRunning simulation with {policy} policy...")
        sim = MultiLevelCacheSimulator(cache_configs, policy, warmup=warmup_accesses)
        sim.process_trace(trace)
        
        # 4. Collect Stats
        policy_stats = {}
        for level in [sim.l1, sim.l2, sim.l3]:
            accesses = level.accesses
            hits = level.hits
            misses = level.misses
            hit_rate = (hits / accesses * 100) if accesses > 0 else 0
            miss_rate = (misses / accesses * 100) if accesses > 0 else 0
            
            policy_stats[level.name] = {
                'accesses': accesses,
                'hits': hits,
                'misses': misses,
                'hit_rate': hit_rate,
                'miss_rate': miss_rate
            }
            
            print(f"  {level.name} - Hit Rate: {hit_rate:5.2f}% | Miss Rate: {miss_rate:5.2f}% | Accesses: {accesses}")
            
        results[policy] = policy_stats

    # 5. Visualization
    plot_results(results)

if __name__ == "__main__":
    main()