"""
app.py — Cache Simulator Dashboard (Streamlit frontend)

Run:  streamlit run app.py
API:  http://localhost:8000  (FastAPI server.py must be running)
"""

import io
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CacheLens — Policy Simulator",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000"
POLICIES = ["FIFO", "LRU", "BELADY", "CUSTOM"]
LEVELS   = ["L1", "L2", "L3"]

POLICY_COLORS = {
    "FIFO":   "#60a5fa",   # blue-400
    "LRU":    "#34d399",   # emerald-400
    "BELADY": "#f59e0b",   # amber-400
    "CUSTOM": "#f472b6",   # pink-400
}

LEVEL_COLORS = {
    "L1": "#818cf8",   # indigo-400
    "L2": "#2dd4bf",   # teal-400
    "L3": "#fb923c",   # orange-400
}

# ---------------------------------------------------------------------------
# Inject custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Import ── */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600;700&display=swap');

/* ── Root reset ── */
html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
}

/* ── Main background ── */
.stApp {
    background: #0d1117;
    color: #e2e8f0;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #111827 !important;
    border-right: 1px solid #1f2937;
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] .stNumberInput input {
    background: #1f2937 !important;
    border: 1px solid #374151 !important;
    border-radius: 6px !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}
section[data-testid="stSidebar"] label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    color: #6b7280 !important;
}

/* ── Headings ── */
h1 { 
    font-family: 'Sora', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.9rem !important;
    background: linear-gradient(135deg, #818cf8 0%, #2dd4bf 100%);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    letter-spacing: -0.03em !important;
}
h2 { color: #94a3b8 !important; font-weight: 600 !important; font-size: 1.1rem !important; }
h3 { color: #64748b !important; font-weight: 400 !important; font-size: 0.9rem !important; }

/* ── Metric cards ── */
.metric-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.metric-card .label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #4b5563;
    margin-bottom: 0.3rem;
}
.metric-card .value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    color: #e2e8f0;
}
.metric-card .sub {
    font-size: 0.72rem;
    color: #6b7280;
    margin-top: 0.15rem;
}

/* ── Policy badge ── */
.policy-badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* ── Tabs ── */
.stTabs [role="tablist"] button {
    font-family: 'Sora', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    color: #6b7280 !important;
}
.stTabs [role="tablist"] button[aria-selected="true"] {
    color: #818cf8 !important;
    border-bottom-color: #818cf8 !important;
}

/* ── Code area ── */
.stTextArea textarea {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
    color: #a5f3fc !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
}

/* ── Button ── */
.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #6366f1, #818cf8) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 0 !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* ── Alerts ── */
.stAlert { border-radius: 8px !important; font-size: 0.82rem !important; }

/* ── Divider ── */
hr { border-color: #1f2937 !important; margin: 1rem 0 !important; }

/* ── Section header ── */
.section-header {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4b5563;
    margin: 1.5rem 0 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1f2937;
}

/* ── Info chip ── */
.chip {
    display: inline-block;
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #9ca3af;
    margin: 0.15rem;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #111827 !important;
    border: 1px dashed #374151 !important;
    border-radius: 10px !important;
}

/* ── Plotly chart container ── */
.js-plotly-plot { border-radius: 10px; overflow: hidden; }

/* ── Winner highlight ── */
.winner-row {
    background: linear-gradient(90deg, #064e3b20, transparent);
    border-left: 3px solid #34d399;
    padding: 0.4rem 0.6rem;
    border-radius: 0 6px 6px 0;
    margin: 0.2rem 0;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Default example program
# ---------------------------------------------------------------------------
DEFAULT_CPP = """\
#include <cstdint>
#include <iostream>
#include <vector>
#include <random>

// L1 Cache is 32KB. Pattern array (16KB) fits easily in L1.
const size_t PATTERN_ELEMENTS = 2048;

// Noise array (256KB) floods the L1 cache — triggers thrashing.
const size_t NOISE_ELEMENTS = 32768;

static uint64_t TraceWorkload() {
    std::vector<uint64_t> pattern_data(PATTERN_ELEMENTS, 1);
    std::vector<uint64_t> noise_data(NOISE_ELEMENTS, 1);
    uint64_t sum = 0;

    std::mt19937 rng(42);
    std::uniform_int_distribution<size_t> dist(0, NOISE_ELEMENTS - 1);

    std::cout << "Executing memory accesses...\\n";

    for (int i = 0; i < 15000; ++i) {
        // PHASE A: Predictable stride — SRD-aware policy thrives
        for (int j = 0; j < 16; ++j) {
            size_t idx = ((i * 16) + j) % PATTERN_ELEMENTS;
            sum += pattern_data[idx];
        }
        // PHASE B: Random noise — LRU struggles under cache thrashing
        for (int j = 0; j < 16; ++j) {
            size_t noise_idx = dist(rng);
            noise_data[noise_idx] += 1;
            sum ^= noise_data[noise_idx];
        }
    }
    return sum;
}

int main() {
    std::cout << "Starting LRU vs SRD cache stress test...\\n";
    uint64_t result = TraceWorkload();
    std::cout << "Done. Integrity check = " << result << "\\n";
    return 0;
}
"""

# ---------------------------------------------------------------------------
# Helpers — API calls
# ---------------------------------------------------------------------------
def _call_simulate_code(code: str, cfg: dict) -> dict:
    payload = {"code": code, "config": cfg}
    try:
        resp = requests.post(f"{API_BASE}/simulate_code", json=payload, timeout=360)
    except requests.ConnectionError:
        return {"status": "error", "message": "Cannot connect to backend", "details": f"Is server.py running at {API_BASE}?"}
    try:
        return resp.json()
    except Exception:
        return {"status": "error", "message": "Bad response from backend", "details": resp.text[:400]}


def _call_simulate_trace(file_bytes: bytes, filename: str, cfg: dict) -> dict:
    params = {k: v for k, v in cfg.items() if k != "warmup"}
    params["warmup"] = cfg["warmup"]
    try:
        resp = requests.post(
            f"{API_BASE}/simulate_trace",
            files={"file": (filename, io.BytesIO(file_bytes), "text/plain")},
            params=params,
            timeout=120,
        )
    except requests.ConnectionError:
        return {"status": "error", "message": "Cannot connect to backend", "details": f"Is server.py running at {API_BASE}?"}
    try:
        return resp.json()
    except Exception:
        return {"status": "error", "message": "Bad response from backend", "details": resp.text[:400]}


# ---------------------------------------------------------------------------
# Sidebar — config
# ---------------------------------------------------------------------------
def render_sidebar() -> dict:
    st.sidebar.markdown("## ⚙️ Cache Parameters")
    st.sidebar.markdown('<div class="section-header">Block & Warmup</div>', unsafe_allow_html=True)

    block_size = st.sidebar.number_input("Block Size (bytes)", value=64, step=64, min_value=16, help="Must be a power of 2. Typical: 64B.")
    warmup     = st.sidebar.number_input("Warmup Accesses", value=50000, step=1000, min_value=0, help="Accesses to skip before recording stats (avoids cold-start bias).")

    st.sidebar.markdown('<div class="section-header">L1 Cache</div>', unsafe_allow_html=True)
    l1_size  = st.sidebar.number_input("L1 Size (bytes)",   value=32768,   step=4096, min_value=256, help="Default: 32 KB")
    l1_assoc = st.sidebar.number_input("L1 Associativity",  value=8,       step=1,    min_value=1,   help="Way count. Power of 2.")

    st.sidebar.markdown('<div class="section-header">L2 Cache</div>', unsafe_allow_html=True)
    l2_size  = st.sidebar.number_input("L2 Size (bytes)",   value=262144,  step=16384, min_value=256, help="Default: 256 KB")
    l2_assoc = st.sidebar.number_input("L2 Associativity",  value=8,       step=1,     min_value=1,   help="Way count. Power of 2.")

    st.sidebar.markdown('<div class="section-header">L3 Cache</div>', unsafe_allow_html=True)
    l3_size  = st.sidebar.number_input("L3 Size (bytes)",   value=2097152, step=65536, min_value=256, help="Default: 2 MB")
    l3_assoc = st.sidebar.number_input("L3 Associativity",  value=16,      step=1,     min_value=1,   help="Way count. Power of 2.")

    def _pow2(n):
        return n > 0 and (n & (n - 1)) == 0

    errors = []
    for name, val in [("block_size", block_size), ("L1_size", l1_size), ("L1_assoc", l1_assoc),
                      ("L2_size", l2_size), ("L2_assoc", l2_assoc), ("L3_size", l3_size), ("L3_assoc", l3_assoc)]:
        if not _pow2(int(val)):
            errors.append(f"**{name}** ({val}) must be a power of 2")

    if l1_size < block_size * l1_assoc:
        errors.append(f"L1 size ({l1_size}) < block_size × L1_assoc ({block_size * l1_assoc})")
    if l2_size < block_size * l2_assoc:
        errors.append(f"L2 size ({l2_size}) < block_size × L2_assoc ({block_size * l2_assoc})")
    if l3_size < block_size * l3_assoc:
        errors.append(f"L3 size ({l3_size}) < block_size × L3_assoc ({block_size * l3_assoc})")

    if errors:
        st.sidebar.error("**Config errors:**\n" + "\n".join(f"- {e}" for e in errors))

    config_valid = len(errors) == 0
    cfg = dict(
        block_size=int(block_size), warmup=int(warmup),
        L1_size=int(l1_size), L1_assoc=int(l1_assoc),
        L2_size=int(l2_size), L2_assoc=int(l2_assoc),
        L3_size=int(l3_size), L3_assoc=int(l3_assoc),
    )

    st.sidebar.divider()
    st.sidebar.markdown("""
<div style="font-size:0.7rem;color:#4b5563;line-height:1.6">
<b>Custom Policy</b> — Stride-aware eviction detects constant-stride 
(streaming) access patterns and evicts those blocks first, reducing 
cache pollution under mixed sequential + random workloads. Falls back 
to LRU when no stride is detected.
</div>
""", unsafe_allow_html=True)

    return cfg, config_valid


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Sora, sans-serif", color="#94a3b8", size=11),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1f2937", borderwidth=1),
    xaxis=dict(gridcolor="#1f2937", zerolinecolor="#1f2937"),
    yaxis=dict(gridcolor="#1f2937", zerolinecolor="#1f2937"),
    margin=dict(l=40, r=20, t=50, b=40),
)


def chart_hit_rates(results: dict):
    fig = go.Figure()
    for level in LEVELS:
        rates = [results[p][level]["hit_rate"] for p in POLICIES]
        fig.add_trace(go.Bar(
            name=level,
            x=POLICIES,
            y=rates,
            marker_color=LEVEL_COLORS[level],
            marker_line_width=0,
            text=[f"{r:.2f}%" for r in rates],
            textposition="outside",
            textfont=dict(size=9, family="JetBrains Mono"),
        ))
    fig.update_layout(
        title=dict(text="Hit Rate by Policy & Cache Level", font=dict(size=13, color="#e2e8f0")),
        barmode="group",
        yaxis_title="Hit Rate (%)",
        yaxis_range=[0, 108],
        **_CHART_LAYOUT,
    )
    return fig


def chart_miss_rates(results: dict):
    fig = go.Figure()
    for level in LEVELS:
        rates = [results[p][level]["miss_rate"] for p in POLICIES]
        fig.add_trace(go.Bar(
            name=level,
            x=POLICIES,
            y=rates,
            marker_color=LEVEL_COLORS[level],
            marker_line_width=0,
            text=[f"{r:.2f}%" for r in rates],
            textposition="outside",
            textfont=dict(size=9, family="JetBrains Mono"),
        ))
    fig.update_layout(
        title=dict(text="Miss Rate by Policy & Cache Level", font=dict(size=13, color="#e2e8f0")),
        barmode="group",
        yaxis_title="Miss Rate (%)",
        yaxis_range=[0, 108],
        **_CHART_LAYOUT,
    )
    return fig


def chart_l1_radar(results: dict):
    """Spider / radar chart for L1 hit rate across policies."""
    categories = POLICIES + [POLICIES[0]]
    values     = [results[p]["L1"]["hit_rate"] for p in POLICIES]
    values.append(values[0])

    fig = go.Figure(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(129,140,248,0.15)",
        line=dict(color="#818cf8", width=2),
        marker=dict(color="#818cf8", size=6),
    ))
    fig.update_layout(
        title=dict(text="L1 Hit Rate — Policy Radar", font=dict(size=12, color="#e2e8f0")),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1f2937", color="#6b7280"),
            angularaxis=dict(gridcolor="#1f2937", color="#6b7280"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Sora, sans-serif", color="#94a3b8", size=11),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def chart_access_breakdown(results: dict, policy: str):
    level_names = LEVELS
    hits   = [results[policy][l]["hits"]   for l in LEVELS]
    misses = [results[policy][l]["misses"] for l in LEVELS]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Hits",   x=LEVELS, y=hits,   marker_color="#34d399", marker_line_width=0))
    fig.add_trace(go.Bar(name="Misses", x=LEVELS, y=misses, marker_color="#f87171", marker_line_width=0))
    fig.update_layout(
        title=dict(text=f"{policy} — Hits vs Misses (absolute)", font=dict(size=12, color="#e2e8f0")),
        barmode="stack",
        yaxis_title="Accesses",
        **_CHART_LAYOUT,
    )
    return fig


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------
def _best_policy(results: dict, level: str, metric: str = "hit_rate") -> str:
    return max(POLICIES, key=lambda p: results[p][level][metric])


def render_results(data: dict):
    results  = data["results"]
    metadata = data["metadata"]

    # ── Metadata chips ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Simulation Summary</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
<div class="metric-card">
  <div class="label">Trace Accesses</div>
  <div class="value">{metadata["trace_length"]:,}</div>
  <div class="sub">total memory ops</div>
</div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
<div class="metric-card">
  <div class="label">Warmup Skipped</div>
  <div class="value">{metadata["warmup_accesses"]:,}</div>
  <div class="sub">cold-start accesses</div>
</div>""", unsafe_allow_html=True)
    with col3:
        cfg = metadata["cache_config"]
        st.markdown(f"""
<div class="metric-card">
  <div class="label">Block Size</div>
  <div class="value">{cfg["block_size"]} B</div>
  <div class="sub">cache line width</div>
</div>""", unsafe_allow_html=True)
    with col4:
        best = _best_policy(results, "L1")
        st.markdown(f"""
<div class="metric-card">
  <div class="label">Best L1 Policy</div>
  <div class="value" style="font-size:1.2rem">{best}</div>
  <div class="sub">{results[best]["L1"]["hit_rate"]:.2f}% hit rate</div>
</div>""", unsafe_allow_html=True)

    # ── Charts ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Policy Comparison Charts</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_hit_rates(results),  use_container_width=True)
    with c2:
        st.plotly_chart(chart_miss_rates(results), use_container_width=True)

    c3, c4 = st.columns([1, 2])
    with c3:
        st.plotly_chart(chart_l1_radar(results), use_container_width=True)
    with c4:
        selected_policy = st.selectbox("Breakdown policy:", POLICIES, index=1)
        st.plotly_chart(chart_access_breakdown(results, selected_policy), use_container_width=True)

    # ── Per-policy stats table ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Detailed Statistics</div>', unsafe_allow_html=True)
    cols = st.columns(len(POLICIES))
    for i, policy in enumerate(POLICIES):
        with cols[i]:
            color = POLICY_COLORS[policy]
            st.markdown(f"""
<div style="border:1px solid {color}33; border-top: 3px solid {color}; 
     border-radius:8px; padding:0.8rem; background:#111827; margin-bottom:0.5rem">
  <div style="font-size:0.7rem; font-weight:700; letter-spacing:0.1em; 
       text-transform:uppercase; color:{color}; margin-bottom:0.6rem">{policy}</div>""",
            unsafe_allow_html=True)

            for level in LEVELS:
                s = results[policy][level]
                is_best = _best_policy(results, level) == policy
                prefix = "🏆 " if is_best else "  "
                st.markdown(f"""
  <div style="margin:0.4rem 0; padding:0.3rem 0; border-bottom:1px solid #1f2937">
    <div style="font-size:0.65rem; color:#6b7280; font-weight:600; letter-spacing:0.06em">{prefix}{level}</div>
    <div style="font-family:'JetBrains Mono',monospace; font-size:0.82rem; color:#e2e8f0">
      {s["hit_rate"]:.1f}% hit · {s["miss_rate"]:.1f}% miss
    </div>
    <div style="font-size:0.65rem; color:#4b5563">
      {s["hits"]:,} hits / {s["accesses"]:,} accesses
    </div>
  </div>""", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    # ── Policy notes ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Policy Notes</div>', unsafe_allow_html=True)
    with st.expander("📖 Understanding the policies", expanded=False):
        st.markdown("""
| Policy | Strategy | Best suited for |
|--------|----------|----------------|
| **FIFO** | Evicts the oldest inserted block regardless of recency | Simple baseline; no metadata overhead |
| **LRU** | Evicts the least recently used block | Temporal locality workloads |
| **BELADY** | Evicts the block with the farthest next use (offline, optimal) | Theoretical upper bound — not implementable online |
| **CUSTOM** | Detects stride/streaming patterns; evicts streaming blocks first, falls back to LRU | Mixed sequential + random workloads; reduces streaming pollution |
""")
        st.info(metadata.get("custom_policy_description", ""))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Header
    st.markdown("# 🧠 CacheLens — Multi-Level Cache Simulator")
    st.markdown(
        '<div style="color:#4b5563;font-size:0.82rem;margin-top:-0.5rem;margin-bottom:1.5rem">'
        'Trace-Driven Multi-Level Cache Policy Simulator · FIFO · LRU · Belady · Stride-Aware Custom'
        '</div>',
        unsafe_allow_html=True,
    )


    cfg, config_valid = render_sidebar()
    
    # ── Input tabs ──────────────────────────────────────────────────────────
    tab_code, tab_trace = st.tabs(["✏️  Write / Paste C++ Code", "📂  Upload Trace File"])

    # ── Tab: Code ───────────────────────────────────────────────────────────
    with tab_code:
        st.markdown("""
<div style="background:#0f1729;border:1px solid #1f2937;border-radius:8px;
     padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.78rem;color:#6b7280;line-height:1.6">
<b style="color:#818cf8">How it works:</b> Your code is saved as <code>test_program.cpp</code>, 
compiled, then instrumented with <b>Intel PIN</b> to capture every memory read/write at runtime. 
The resulting trace drives the cache simulator across all four replacement policies.<br><br>
<b style="color:#818cf8">Good experiments:</b> Programs with a mix of sequential array traversal 
(temporal/spatial locality) and random memory access patterns produce the most interesting 
policy comparisons.
</div>
""", unsafe_allow_html=True)

        code = st.text_area(
            "C++ source code",
            value=DEFAULT_CPP,
            height=400,
            label_visibility="collapsed",
        )

        run_code = st.button("▶  Compile, Trace & Simulate", disabled=not config_valid, key="run_code")

    # ── Tab: Trace ───────────────────────────────────────────────────────────
    with tab_trace:
        st.markdown("""
<div style="background:#0f1729;border:1px solid #1f2937;border-radius:8px;
     padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.78rem;color:#6b7280;line-height:1.6">
<b style="color:#818cf8">Expected format</b> — one memory access per line:
<pre style="margin:0.5rem 0;color:#a5f3fc;font-size:0.76rem">R 0x7fffc6606f58   # Read from address
W 0x7fffc6606f60   # Write to address
#eof               # Optional end marker</pre>
Both <b>hexadecimal</b> (<code>0x...</code>) and <b>decimal</b> addresses are supported. 
Malformed lines are silently skipped.
</div>
""", unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Drop your PIN trace file here",
            type=["txt", "out", "trace", "log"],
            help="Typically named pin_tracer.out or memory_trace.txt",
        )
        if uploaded:
            st.success(f"✓ Loaded **{uploaded.name}** ({uploaded.size:,} bytes)")

        run_trace = st.button("▶  Simulate Uploaded Trace", disabled=(not config_valid or uploaded is None), key="run_trace")

    # ── Execution ─────────────────────────────────────────────────────────
    if "result_data" not in st.session_state:
        st.session_state.result_data = None
    if "result_error" not in st.session_state:
        st.session_state.result_error = None

    if run_code:
        st.session_state.result_data  = None
        st.session_state.result_error = None
        with st.spinner("🔨 Compiling → 🔍 PIN tracing → ⚙️ Simulating…"):
            resp = _call_simulate_code(code, cfg)
        if resp.get("status") == "success":
            st.session_state.result_data = resp["data"]
            st.toast("✅ Simulation complete!", icon="✅")
        else:
            st.session_state.result_error = resp

    if run_trace and uploaded is not None:
        st.session_state.result_data  = None
        st.session_state.result_error = None
        file_bytes = uploaded.read()
        with st.spinner("⚙️ Parsing trace and running simulation…"):
            resp = _call_simulate_trace(file_bytes, uploaded.name, cfg)
        if resp.get("status") == "success":
            st.session_state.result_data = resp["data"]
            st.toast("✅ Simulation complete!", icon="✅")
        else:
            st.session_state.result_error = resp

    # ── Display results or errors ──────────────────────────────────────────
    if st.session_state.result_error:
        err = st.session_state.result_error
        st.divider()
        st.error(f"**{err.get('message', 'Unknown error')}**")
        details = err.get("details") or err.get("detail", {})
        if details:
            with st.expander("🔍 Error details"):
                if isinstance(details, dict):
                    st.json(details)
                else:
                    st.code(str(details), language="text")

    if st.session_state.result_data:
        st.divider()
        render_results(st.session_state.result_data)

    # ── Empty state ────────────────────────────────────────────────────────
    if not st.session_state.result_data and not st.session_state.result_error:
        st.markdown("""
<div style="text-align:center;padding:3rem 0 2rem;color:#374151">
  <div style="font-size:2.5rem;margin-bottom:0.5rem">⚡</div>
  <div style="font-size:0.9rem;font-weight:600;color:#4b5563">Ready to simulate</div>
  <div style="font-size:0.75rem;color:#374151;margin-top:0.3rem">
    Configure cache parameters in the sidebar, then choose an input method above.
  </div>
</div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
