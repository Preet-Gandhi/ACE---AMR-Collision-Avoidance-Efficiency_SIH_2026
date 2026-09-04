from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from dashboard.snapshot import normalize_snapshot
from dashboard.svg_view import SvgWarehouseRenderer
from dashboard.warehouse_env import WarehouseEnvironment

# Page Configuration
st.set_page_config(
    page_title="ACE — AMR Collision Avoidance",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Dark clean styling focusing on the warehouse
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
        padding: 8px 12px;
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
        margin-top: 10px;
        margin-bottom: 8px;
    }
    .legend-bar {
        display: flex;
        justify-content: center;
        gap: 20px;
        font-size: 13px;
        color: #94a3b8;
        margin-top: 6px;
        margin-bottom: 14px;
        flex-wrap: wrap;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .control-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize simulation environment in session state
if "warehouse_env" not in st.session_state:
    env = WarehouseEnvironment(num_robots=3)
    env.randomize_pickups(count=3)
    st.session_state["warehouse_env"] = env

env: WarehouseEnvironment = st.session_state["warehouse_env"]
raw_snapshot = env.get_snapshot()
normalized = normalize_snapshot(raw_snapshot)
metrics = normalized.metrics

# Title
st.markdown("<h2 style='text-align:center; margin-bottom:8px;'>ACE — AMR Collision Avoidance</h2>", unsafe_allow_html=True)

# 4 Compact KPIs
c1, c2, c3, c4 = st.columns(4)

total_tasks = metrics.total_tasks or len(normalized.tasks) or 3
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

# Main Hero Visual: Animated Warehouse Floor
st.markdown("<div class='warehouse-container'>", unsafe_allow_html=True)
svg_code = SvgWarehouseRenderer.render_svg(
    normalized,
    shelves=set(env.SHELF_BLOCKS),
    custom_obstacles=set(env.custom_obstacles),
    dropoff_cells=env.DROPOFF_CELLS,
)
st.markdown(svg_code, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Clean Legend
st.markdown(
    """
    <div class='legend-bar'>
        <span class='legend-item'><span style='color:#10b981; font-size:16px;'>●</span> Moving</span>
        <span class='legend-item'><span style='color:#f59e0b; font-size:16px;'>●</span> Waiting</span>
        <span class='legend-item'><span style='color:#ef4444; font-size:16px;'>●</span> Conflict</span>
        <span class='legend-item'><span style='color:#94a3b8; font-size:16px;'>●</span> Idle</span>
        <span style='color:#334155;'>|</span>
        <span class='legend-item'><span style='background:#1e3a8a; border:1px solid #3b82f6; border-radius:3px; padding:1px 5px; font-size:10px; color:#bfdbfe; font-weight:bold;'>P</span> Aisle Pickup</span>
        <span class='legend-item'><span style='background:#064e3b; border:1px solid #10b981; border-radius:3px; padding:1px 5px; font-size:10px; color:#a7f3d0; font-weight:bold;'>D</span> Dropoff Station</span>
        <span class='legend-item'><span style='background:#1e293b; border:1px solid #475569; border-radius:3px; padding:1px 6px; font-size:10px;'>RACK</span> Storage Shelf</span>
        <span class='legend-item'><span style='background:#7c2d12; border:1px solid #ea580c; border-radius:3px; padding:1px 5px; font-size:10px;'>⚠️</span> Custom Obstacle</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Compact Interactive Controls (Task Pickups & Dynamic Obstacles)
st.markdown("<hr style='border-color:#1e293b; margin: 10px 0;'>", unsafe_allow_html=True)
col_tasks, col_obs, col_sim = st.columns([4, 4, 3])

with col_tasks:
    st.markdown("##### 📦 Pickup Tasks")
    tc1, tc2 = st.columns([1, 1])
    with tc1:
        if st.button("🎲 Randomize Pickups", use_container_width=True):
            env.reset()
            env.randomize_pickups(count=3)
            st.rerun()

    with tc2:
        # Manual Aisle Pickup Assignment
        aisle_options = [pos for pos in env.AISLE_CELLS if pos not in env.custom_obstacles][:12]
        chosen_pickup = st.selectbox("Select Aisle Cell", options=aisle_options, format_func=lambda p: f"Aisle {p}")
        if st.button("Assign Selected Pickup", use_container_width=True):
            try:
                env.spawn_task(chosen_pickup)
                st.rerun()
            except Exception as e:
                st.error(str(e))

with col_obs:
    st.markdown("##### ⚠️ Custom Obstacles")
    valid_obs_cells = [pos for pos in env.AISLE_CELLS if pos not in env.custom_obstacles][:15]
    obs_pos = st.selectbox("Aisle Position for Obstacle", options=valid_obs_cells, format_func=lambda p: f"Cell {p}")
    oc1, oc2 = st.columns(2)
    with oc1:
        if st.button("➕ Place Obstacle", use_container_width=True):
            if env.add_custom_obstacle(obs_pos):
                st.success(f"Obstacle at {obs_pos} triggered replan!")
                st.rerun()
    with oc2:
        if st.button("🧹 Clear Obstacles", use_container_width=True):
            for obs in list(env.custom_obstacles):
                env.remove_custom_obstacle(obs)
            st.rerun()

with col_sim:
    st.markdown("##### ⚙️ Simulation Clock")
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("▶ Step Clock", use_container_width=True):
            env.step()
            st.rerun()
    with sc2:
        if st.button("🔄 Reset All", use_container_width=True):
            env.reset()
            env.randomize_pickups(count=3)
            st.rerun()
