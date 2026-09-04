from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from dashboard.demo_data import get_fixed_demo_snapshot
from dashboard.snapshot import normalize_snapshot
from dashboard.svg_view import SvgWarehouseRenderer

# Page Configuration
st.set_page_config(
    page_title="ACE — AMR Collision Avoidance",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Clean, modern dark aesthetics
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    .kpi-box {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
    }
    .kpi-val {
        font-size: 22px;
        font-weight: 700;
        color: #38bdf8;
    }
    .kpi-lbl {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        color: #94a3b8;
        letter-spacing: 0.5px;
    }
    .warehouse-container {
        display: flex;
        justify-content: center;
        margin-top: 14px;
        margin-bottom: 10px;
    }
    .legend-bar {
        display: flex;
        justify-content: center;
        gap: 24px;
        font-size: 13px;
        color: #94a3b8;
        margin-top: 8px;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Retrieve snapshot (uses session state if injected by simulation, else fixed demo)
snapshot_data = st.session_state.get("live_snapshot", get_fixed_demo_snapshot())
normalized = normalize_snapshot(snapshot_data)
metrics = normalized.metrics

# Title
st.markdown("<h2 style='text-align:center; margin-bottom:12px;'>ACE — AMR Collision Avoidance</h2>", unsafe_allow_html=True)

# 4 Compact KPIs
c1, c2, c3, c4 = st.columns(4)

total_tasks = metrics.total_tasks or len(normalized.tasks) or 6
tasks_str = f"{metrics.tasks_completed} / {total_tasks}"

with c1:
    st.markdown(f"<div class='kpi-box'><div class='kpi-lbl'>Tasks Completed</div><div class='kpi-val'>{tasks_str}</div></div>", unsafe_allow_html=True)

with c2:
    col_color = "#ef4444" if metrics.collisions > 0 else "#10b981"
    st.markdown(f"<div class='kpi-box'><div class='kpi-lbl'>Collisions</div><div class='kpi-val' style='color:{col_color};'>{metrics.collisions}</div></div>", unsafe_allow_html=True)

with c3:
    dl_color = "#ef4444" if metrics.deadlocks > 0 else "#10b981"
    st.markdown(f"<div class='kpi-box'><div class='kpi-lbl'>Deadlocks</div><div class='kpi-val' style='color:{dl_color};'>{metrics.deadlocks}</div></div>", unsafe_allow_html=True)

with c4:
    st.markdown(f"<div class='kpi-box'><div class='kpi-lbl'>Replans</div><div class='kpi-val'>{metrics.replanning_count}</div></div>", unsafe_allow_html=True)

# Main Visual: Animated Warehouse Floor
st.markdown("<div class='warehouse-container'>", unsafe_allow_html=True)
svg_code = SvgWarehouseRenderer.render_svg(normalized)
st.markdown(svg_code, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Simple Legend underneath
st.markdown(
    """
    <div class='legend-bar'>
        <span class='legend-item'><span style='color:#10b981; font-size:16px;'>●</span> Moving</span>
        <span class='legend-item'><span style='color:#f59e0b; font-size:16px;'>●</span> Waiting</span>
        <span class='legend-item'><span style='color:#ef4444; font-size:16px;'>●</span> Conflict</span>
        <span class='legend-item'><span style='color:#94a3b8; font-size:16px;'>●</span> Idle</span>
        <span style='color:#475569;'>|</span>
        <span class='legend-item'><span style='background:#1e3a8a; border:1px solid #3b82f6; border-radius:3px; padding:1px 5px; font-size:10px; color:#bfdbfe; font-weight:bold;'>P</span> Pickup</span>
        <span class='legend-item'><span style='background:#064e3b; border:1px solid #10b981; border-radius:3px; padding:1px 5px; font-size:10px; color:#a7f3d0; font-weight:bold;'>D</span> Dropoff</span>
        <span class='legend-item'><span style='background:#1e293b; border:1px solid #475569; border-radius:3px; padding:1px 6px; font-size:10px;'>██</span> Shelf Rack</span>
    </div>
    """,
    unsafe_allow_html=True,
)
