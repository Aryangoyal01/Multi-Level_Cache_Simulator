# PIN Memory Tracer + Cache Simulator

This workspace contains:
- pin_tracer.cpp: Intel PIN tool that logs memory reads/writes as trace lines.
- cache_sim.cpp: C++ cache simulator that replays the trace and reports HIT/MISS.
- sample_trace.txt: Tiny test trace.

## 1) Build PIN tracer

Build inside a PIN source/tools directory using PIN's make system. Example:

```bash
make TARGET=intel64 obj-intel64/pin_tracer.so
```

Run tracer against a target app:

```bash
pin -t obj-intel64/pin_tracer.so -o pin_tracer.out -- ./your_program
```

Output format:

```text
R 0xADDRESS
W 0xADDRESS
...
#eof
```

## 2) Build cache simulator

```bash
g++ -std=c++17 -O2 -o cache_sim cache_sim.cpp
```

## 3) Run cache simulator

```bash
./cache_sim <cache_size_bytes> <block_size_bytes> <associativity> <trace_file> <output_file>
```

Example:

```bash
./cache_sim 16384 64 4 pin_tracer.out cache_results.txt
```

Sample run with included trace:

```bash
./cache_sim 16 4 4 sample_trace.txt sample_results.txt
```

## Notes

- Parameters require power-of-two block size, associativity, and number of sets.
- Replacement policy is LRU.
