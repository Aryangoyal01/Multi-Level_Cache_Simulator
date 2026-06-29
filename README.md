# Multi-Level Cache Simulator (Trace-Driven with Custom Policy)

> A full-stack cache simulator powered by **Intel PIN + Python + FastAPI + Streamlit**
> Analyze real memory traces and compare cache replacement policies interactively.

---

## Features

* 🔹 3-Level Cache Simulation (L1, L2, L3)
* 🔹 Replacement Policies:

  * FIFO
  * LRU
  * Belady (Optimal)
  * Custom (Stride-aware)
* 🔹 Real trace-driven simulation via Intel PIN
* 🔹 CLI + Web Interface
* 🔹 Interactive Plotly charts
* 🔹 Upload trace or generate via C++

---

## Architecture

```bash
C++ Program
   ↓
Intel PIN (Tracer)
   ↓
pin_tracer.out
   ↓
Python Cache Simulator
   ↓
FastAPI Backend
   ↓
Streamlit Frontend
```

---

## Requirements

### System

* Linux / WSL (required)
* Intel PIN
* g++, make

### Python

* Python 3.8+

---

## Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip g++ make
```

```bash
pip install -r requirements.txt --break-system-packages
```

---

## Setup Intel PIN

```bash
tar -xvf pin-*.tar.gz
export PIN_ROOT=/path/to/pin
export PATH=$PIN_ROOT:$PATH
```

(Optional)

```bash
echo 'export PIN_ROOT=/path/to/pin' >> ~/.bashrc
echo 'export PATH=$PIN_ROOT:$PATH' >> ~/.bashrc
```

---

## Build PIN Tool

```bash
cd pin
make clean
make
```

Verify:

```bash
ls obj-intel64/pin_tracer.so
```

---

## Generate Trace

```bash
cd pin
g++ test_program.cpp -o a.out
```

```bash
$PIN_ROOT/pin -t obj-intel64/pin_tracer.so -- ./a.out
```

Output:

```bash
pin_tracer.out
```

---

## Run CLI Simulator

```bash
cd ..
python main.py
```

Use:

```bash
pin_tracer.out
```

---

## Run Web App

### Backend

```bash
python -m uvicorn web.backend.server:app --reload
```

### Frontend (new terminal)

```bash
python -m streamlit run web/frontend/app.py
```

---

## Open in Browser

```bash
http://localhost:8501
```

---

## Usage

### 🔹 Upload Mode

* Upload `pin_tracer.out`
* Configure cache
* Run simulation

### 🔹 Code Mode

* Write C++ code
* Click run
* Full pipeline executes automatically

---

## Recommended Config

```bash
Block Size: 64
L1: 32768 (8-way)
L2: 262144 (8-way)
L3: 2097152 (16-way)
Warmup: 50000
```

---

## Expected Results

```bash
L1 ≈ 99%
L2 ≈ 60–65%
L3 ≈ ~20%
```

---

## Replacement Policies

| Policy | Description                  |
| ------ | ---------------------------- |
| FIFO   | Oldest block eviction        |
| LRU    | Least recently used          |
| Belady | Optimal (future-aware)       |
| Custom | Stride/stream-aware eviction |

---

## Project Structure

```bash
ca/
├── main.py
├── requirements.txt
├── README.md
│
├── pin/
│   ├── pin_tracer.cpp
│   ├── test_program.cpp
│   └── Makefile
│
├── web/
│   ├── backend/server.py
│   ├── frontend/app.py
│   └── simulator/cache_sim.py
```

---

## Notes

* Always run from project root
* Use `pin_tracer.out` consistently
* Large traces (>200MB) may fail upload
* PIN required → Linux only

---

## Future Work

* Write-back / write-through policies
* Non-inclusive caches
* ML-based replacement
* Docker support

---

## Author

Aryan

---

## Built with Love
---

## Support

If this helped you:

👉 Give it a star ⭐
👉 Share it
👉 Fork it

---

## Summary

A realistic, extensible system that bridges **cache theory + real-world execution** using trace-driven simulation.
