"""
server.py — FastAPI backend for the Cache Simulator Dashboard.
Handles: code compilation → PIN tracing → cache simulation → JSON results.
"""

import os
import subprocess
import logging
import tempfile
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional

from cache_sim import run_simulation, parse_trace

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Cache Simulator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Project directory — ~/ca (or override with CA_DIR env var)
# ---------------------------------------------------------------------------
CA_DIR = Path(os.environ.get("CA_DIR", os.path.expanduser("~/ca"))).resolve()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class CacheConfig(BaseModel):
    block_size: int = 64
    L1_size: int = 32768
    L1_assoc: int = 8
    L2_size: int = 262144
    L2_assoc: int = 8
    L3_size: int = 2097152
    L3_assoc: int = 16
    warmup: int = 50000

    @validator("block_size", "L1_size", "L1_assoc", "L2_size", "L2_assoc", "L3_size", "L3_assoc")
    def must_be_power_of_two(cls, v, field):
        if v <= 0 or (v & (v - 1)) != 0:
            raise ValueError(f"{field.name} must be a positive power of 2, got {v}")
        return v

    @validator("L1_size")
    def l1_big_enough(cls, v, values):
        bs = values.get("block_size", 64)
        assoc = values.get("L1_assoc", 8)
        if v < bs * assoc:
            raise ValueError(f"L1_size ({v}) must be >= block_size * L1_assoc ({bs * assoc})")
        return v

    @validator("L2_size")
    def l2_big_enough(cls, v, values):
        bs = values.get("block_size", 64)
        assoc = values.get("L2_assoc", 8)
        if v < bs * assoc:
            raise ValueError(f"L2_size ({v}) must be >= block_size * L2_assoc ({bs * assoc})")
        return v

    @validator("L3_size")
    def l3_big_enough(cls, v, values):
        bs = values.get("block_size", 64)
        assoc = values.get("L3_assoc", 16)
        if v < bs * assoc:
            raise ValueError(f"L3_size ({v}) must be >= block_size * L3_assoc ({bs * assoc})")
        return v


class SimulateCodeRequest(BaseModel):
    code: str
    config: CacheConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ok(data: dict) -> dict:
    return {"status": "success", "data": data}


def _err(message: str, details: str = "") -> dict:
    return {"status": "error", "message": message, "details": details}


def _run(cmd: list[str], cwd: Path, timeout: int = 120, label: str = "") -> subprocess.CompletedProcess:
    """Run a subprocess, raise HTTPException on failure."""
    log.info("[%s] Running: %s  (cwd=%s)", label, " ".join(cmd), cwd)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=_err(
                f"{label} timed out after {timeout}s",
                "The process ran too long. Simplify the program or increase the timeout.",
            ),
        )
    if result.returncode != 0:
        raise HTTPException(
            status_code=422,
            detail=_err(
                f"{label} failed (exit {result.returncode})",
                (result.stderr or result.stdout or "No output captured").strip(),
            ),
        )
    log.info("[%s] OK. stdout=%s", label, result.stdout[:200])
    return result


def _build_metadata(trace: list[int], config: CacheConfig, source: str) -> dict:
    return {
        "trace_length": len(trace),
        "warmup_accesses": config.warmup,
        "source": source,
        "cache_config": config.dict(),
        "custom_policy_description": (
            "Stride-aware eviction: detects constant-stride (streaming) access patterns "
            "over the last 3 accesses. Streaming blocks are evicted first to reduce "
            "cache pollution; falls back to LRU when no streaming pattern is detected."
        ),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "ca_dir": str(CA_DIR)}


@app.post("/simulate_code")
def simulate_code(body: SimulateCodeRequest):
    """
    Full pipeline:
      1. Write C++ code → test_program.cpp
      2. make clean
      3. Compile test program
      4. Build PIN tool (make pintool)
      5. Run PIN → memory_trace.txt
      6. Parse trace → run simulation → return results
    """
    if not CA_DIR.exists():
        raise HTTPException(
            status_code=500,
            detail=_err(
                f"Project directory not found: {CA_DIR}",
                "Set the CA_DIR environment variable to the correct path.",
            ),
        )

    # 1. Write source
    src_path = CA_DIR / "test_program.cpp"
    trace_path = CA_DIR / "memory_trace.txt"
    log.info("Writing source to %s", src_path)
    src_path.write_text(body.code, encoding="utf-8")

    # 2. make clean
    _run(["make", "clean"], cwd=CA_DIR, timeout=30, label="make clean")

    # 3. Compile
    _run(
        ["make", "test_program"],
        cwd=CA_DIR,
        timeout=60,
        label="Compile test_program",
    )
    if not (CA_DIR / "test_program").exists():
        raise HTTPException(
            status_code=422,
            detail=_err(
                "Compilation succeeded but binary 'test_program' not found.",
                "Check your Makefile target name.",
            ),
        )

    # 4. Build PIN tool
    _run(
        ["make", "pintool"],
        cwd=CA_DIR,
        timeout=120,
        label="Build PIN tool",
    )

    # 5. Run PIN
    pin_binary = shutil.which("pin") or os.environ.get("PIN_ROOT", "") + "/pin"
    pintool_so = CA_DIR / "obj-intel64" / "pin_tracer.so"
    if not pintool_so.exists():
        raise HTTPException(
            status_code=422,
            detail=_err(
                f"PIN tool shared object not found: {pintool_so}",
                "Ensure the PIN tool built correctly and obj-intel64/ exists.",
            ),
        )

    _run(
        [
            pin_binary,
            "-t", str(pintool_so),
            "-o", str(trace_path),
            "--", str(CA_DIR / "test_program"),
        ],
        cwd=CA_DIR,
        timeout=300,
        label="PIN tracing",
    )

    # 6. Verify trace
    if not trace_path.exists():
        raise HTTPException(
            status_code=422,
            detail=_err(
                "PIN tracing completed but memory_trace.txt was not created.",
                "Check PIN output and tracer configuration.",
            ),
        )

    raw = trace_path.read_text(encoding="utf-8", errors="replace")
    trace = parse_trace(raw)
    if not trace:
        raise HTTPException(
            status_code=422,
            detail=_err(
                "Trace file exists but contains no valid addresses.",
                raw[:500],
            ),
        )

    log.info("Trace loaded: %d addresses", len(trace))

    # 7. Simulate
    results = run_simulation(trace, body.config.dict())
    metadata = _build_metadata(trace, body.config, source="pin_trace")
    return _ok({"results": results, "metadata": metadata})


@app.post("/simulate_trace")
async def simulate_trace(
    file: UploadFile = File(...),
    block_size: int = 64,
    L1_size: int = 32768,
    L1_assoc: int = 8,
    L2_size: int = 262144,
    L2_assoc: int = 8,
    L3_size: int = 2097152,
    L3_assoc: int = 16,
    warmup: int = 50000,
):
    """
    Direct trace upload pipeline:
      1. Accept uploaded trace file
      2. Parse addresses
      3. Run simulation
      4. Return results
    """
    config_dict = dict(
        block_size=block_size,
        L1_size=L1_size,
        L1_assoc=L1_assoc,
        L2_size=L2_size,
        L2_assoc=L2_assoc,
        L3_size=L3_size,
        L3_assoc=L3_assoc,
        warmup=warmup,
    )

    # Validate config via Pydantic
    try:
        config = CacheConfig(**config_dict)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=_err("Invalid cache configuration", str(exc)))

    raw = (await file.read()).decode("utf-8", errors="replace")
    trace = parse_trace(raw)
    if not trace:
        raise HTTPException(
            status_code=422,
            detail=_err(
                "Uploaded trace contains no valid addresses.",
                "Expected format: 'R 0xADDR' or 'W 0xADDR' per line.",
            ),
        )

    log.info("Uploaded trace: %d addresses", len(trace))
    results = run_simulation(trace, config.dict())
    metadata = _build_metadata(trace, config, source="uploaded_trace")
    return _ok({"results": results, "metadata": metadata})
