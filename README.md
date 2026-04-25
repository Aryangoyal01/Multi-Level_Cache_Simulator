# 🧠 Trace-Driven Multi-Level Cache Simulator with Custom Replacement Policy

## 📌 Overview

This project implements a **trace-driven, multi-level cache simulator** integrated with an **Intel PIN-based memory tracer**. It enables detailed analysis of cache behavior across **L1, L2, and L3 levels** using real execution traces.

The system supports multiple replacement policies:

* **FIFO (First-In-First-Out)**
* **LRU (Least Recently Used)**
* **Belady’s Optimal Algorithm (offline optimal)**
* **Custom Policy (Stride-aware / Streaming-aware eviction)**

The simulator processes real memory access traces and provides **quantitative comparisons** via hit/miss statistics and visualization.

---

## 🏗️ Architecture

```
Target Program
      │
      ▼
Intel PIN Tracer (C++)
      │
      ▼
Memory Trace (R/W addresses)
      │
      ▼
Python Cache Simulator
      │
      ▼
Statistics + Visualization (PNG)
```

---

## 🔧 Components

### 1. Intel PIN Tracer (`pin_tracer.cpp`)

* Instruments every memory read/write
* Outputs trace in format:

```
R 0xADDRESS
W 0xADDRESS
...
#eof
```

* Uses dynamic binary instrumentation to capture **real execution behavior**

---

### 2. Workload Generator (`test_program.cpp`)

* Designed to stress cache policies:

  * **Sequential pattern access** → promotes reuse
  * **Random noise access** → causes cache thrashing

👉 This creates a controlled environment where different policies behave differently.

---

### 3. Cache Simulator (`cache_sim.py`, `main.py`)

#### Features:

* Multi-level cache (L1, L2, L3)
* Inclusive hierarchy
* Configurable:

  * Cache sizes
  * Associativity
  * Block size
* Warmup phase support
* Real trace-driven simulation

---

## 🧠 Replacement Policies

### FIFO

Evicts the oldest inserted block.

### LRU

Evicts the least recently used block.

### Belady (Optimal)

Uses future knowledge to evict the block with the farthest next use.

### 🔥 Custom Policy (Stride-aware)

The custom policy detects **streaming/stride access patterns**:

* Tracks last 3 accesses
* If constant stride detected → marks block as *streaming*
* Evicts streaming blocks first (low reuse probability)
* Falls back to LRU otherwise

👉 This approximates **reuse distance** and improves performance under mixed workloads.

---

## ⚙️ Requirements

### System

* Linux (recommended)
* Intel PIN Tool

### Python

* Python 3.8+

### Libraries

```bash
pip install matplotlib numpy
```

#### Why these are needed:

* **matplotlib** → generates comparison plots (`policy_comparison.png`)
* **numpy** → efficient numerical operations for plotting

---

## 🚀 Setup & Execution

### Step 1: Build PIN Tool

Inside Intel PIN tools directory:

```bash
make TARGET=intel64 obj-intel64/pin_tracer.so
```

---

### Step 2: Compile Test Program

```bash
g++ -O2 test_program.cpp -o test_program
```

---

### Step 3: Generate Memory Trace

```bash
pin -t obj-intel64/pin_tracer.so -o pin_tracer.out -- ./test_program
```

This produces:

```
pin_tracer.out
```

---

### Step 4: Run Cache Simulator

```bash
python3 main.py
```

You will be prompted for:

* Block size
* Cache sizes (L1, L2, L3)
* Associativity
* Warmup accesses
* Trace file path

(Default values are provided for convenience)

---

## 📊 Output

### Terminal Output

Displays per-policy statistics:

```
L1 - Hit Rate: XX%
L2 - Hit Rate: XX%
L3 - Hit Rate: XX%
```

---

### Visualization

A comparison plot is generated:

```
policy_comparison.png
```

This shows:

* L1 / L2 / L3 hit rates
* Across all policies

---

## 🧪 Trace Format

Each line represents a memory access:

```
R 0x7fffc6606f58   # Read
W 0x7fffc6606f60   # Write
```

* Supports both hexadecimal and decimal addresses
* Parser automatically extracts valid addresses

---

## ⚠️ Important Notes

* Cache parameters must be **powers of two**
* Cache size must satisfy:

  ```
  size ≥ block_size × associativity
  ```
* Warmup phase avoids skewed statistics
* Large trace files may require significant memory

---

## 📁 Project Structure

```
.
├── cache_sim.py
├── main.py
├── pin_tracer.cpp
├── test_program.cpp
├── Makefile
├── README.md
```

---

## 🔬 Key Concepts Demonstrated

* Trace-driven simulation
* Multi-level cache hierarchy
* Inclusion property
* Replacement policy design
* Belady optimal algorithm
* Stride-based access pattern detection

---

## 🚀 Future Improvements

* Add write policies (write-back / write-through)
* Support non-inclusive caches
* Parallel simulation for large traces
* Advanced ML-based replacement policy

---

## 👨‍💻 Author

Developed as a systems-level project exploring **cache behavior, replacement policies, and performance optimization**.

---

## 📌 Summary

This project provides a **realistic and extensible framework** for analyzing cache performance using actual execution traces, bridging the gap between theoretical policies and practical behavior.

---
