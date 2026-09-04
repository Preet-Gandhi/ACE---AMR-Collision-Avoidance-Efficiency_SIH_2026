from __future__ import annotations

import sys
import time
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

# Dark clean robotics styling focusing on alignment, contrast, and hierarchy
st.markdown(
    """
    <style>
    /* Permanently hide native Streamlit left sidebar and collapse controls */
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 1560px;
    }
    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #1f2937;
        padding-bottom: 6px;
        margin-bottom: 8px;
    }
    .header-title {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #f8fafc;
        margin: 0;
    }
    .header-badge {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 11px;
        color: #94a3b8;
        font-family: ui-monospace, monospace;
    }
    .badge-loop {
        color: #34d399;
        font-weight: 700;
    }
    .badge-clock {
        color: #fbbf24;
        font-weight: 700;
    }
    .kpi-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 6px 10px;
        text-align: center;
        height: 52px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .kpi-label {
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        color: #94a3b8;
        letter-spacing: 0.7px;
        margin-bottom: 2px;
    }
    .kpi-value {
        font-size: 20px;
        font-weight: 700;
        line-height: 1;
        color: #38bdf8;
        font-family: ui-monospace, monospace;
        text-shadow: 0 0 16px rgba(56,189,248,.18);
    }
    .kpi-card {
        position: relative;
        overflow: hidden;
        transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
    }
    .kpi-card::after {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(110deg, transparent 35%, rgba(255,255,255,.045) 50%, transparent 65%);
        transform: translateX(-120%);
        animation: kpiSweep 4.5s ease-in-out infinite;
        pointer-events: none;
    }
    .kpi-card:hover {
        transform: translateY(-1px);
        border-color: #334155;
        box-shadow: 0 8px 24px rgba(0,0,0,.22);
    }
    .mission-strip {
        display:flex; align-items:center; gap:10px; margin:7px 0 8px; padding:7px 10px;
        border:1px solid #1e293b; border-radius:8px; background:#0f172a;
        font-size:10px; color:#94a3b8;
    }
    .mission-progress {
        flex:1; height:5px; border-radius:99px; background:#1e293b; overflow:hidden;
    }
    .mission-progress > span {
        display:block; height:100%; border-radius:99px; background:#10b981;
        box-shadow:0 0 12px rgba(16,185,129,.45); transition:width .35s ease;
    }
    .live-dot {
        width:7px; height:7px; border-radius:50%; background:#10b981;
        box-shadow:0 0 0 0 rgba(16,185,129,.55); animation: livePulse 1.7s infinite;
    }
    @keyframes kpiSweep { 0%,60% { transform:translateX(-120%); } 85%,100% { transform:translateX(120%); } }
    @keyframes livePulse { 0% { box-shadow:0 0 0 0 rgba(16,185,129,.55); } 70% { box-shadow:0 0 0 7px rgba(16,185,129,0); } 100% { box-shadow:0 0 0 0 rgba(16,185,129,0); } }
    .warehouse-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        background: #080d1a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 8px 12px;
        margin-top: 8px;
        margin-bottom: 6px;
    }
    .warehouse-wrapper svg {
        max-height: 46vh !important;
        width: auto !important;
        max-width: 100% !important;
    }
    .legend-row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        font-size: 11px;
        color: #94a3b8;
        margin-top: 2px;
        margin-bottom: 8px;
        flex-wrap: wrap;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .robot-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 6px 8px;
        font-size: 11px;
        margin-bottom: 4px;
    }
    .robot-title {
        font-weight: 700;
        font-size: 11px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2px;
    }
    .benchmark-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 8px 12px;
        margin-top: 8px;
        margin-bottom: 4px;
    }
    .control-panel {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 10px 12px;
    }
    .panel-title {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: #e2e8f0;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .stButton > button {
        padding: 3px 6px !important;
        min-height: 26px !important;
        font-size: 11px !important;
    }
    div[data-testid="stNumberInput"] input {
        padding: 2px 6px !important;
        font-size: 11px !important;
    }
    div[data-testid="stSelectbox"] select {
        padding: 2px 6px !important;
        font-size: 11px !important;
    }
    .status-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 700;
        padding: 1px 6px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .status-available { background: #064e3b; color: #34d399; border: 1px solid #059669; }
    .status-rack { background: #1f2937; color: #94a3b8; border: 1px solid #374151; }
    .status-obstacle { background: #7c2d12; color: #fb923c; border: 1px solid #ea580c; }
    .status-dropoff { background: #064e3b; color: #a7f3d0; border: 1px solid #10b981; }
    .status-charger { background: #1e3a8a; color: #93c5fd; border: 1px solid #3b82f6; }
    .status-blocked { background: #7f1d1d; color: #f87171; border: 1px solid #dc2626; }
    .chip-container {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
        margin-top: 4px;
    }
    .obs-chip {
        background: #1f2937;
        border: 1px solid #ea580c;
        border-radius: 4px;
        padding: 1px 6px;
        font-size: 10px;
        color: #fb923c;
        font-family: ui-monospace, monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Configuration presets
PRESET_DIMS = {
    "14x10 (Default)": (14, 10),
    "15x9": (15, 9),
    "20x12": (20, 12),
    "30x20": (30, 20),
    "40x40": (40, 40),
}

# Session State Initialization
if "cfg_dim" not in st.session_state:
    st.session_state["cfg_dim"] = "14x10 (Default)"
if "cfg_robots" not in st.session_state:
    st.session_state["cfg_robots"] = 3
if "cfg_packages" not in st.session_state:
    st.session_state["cfg_packages"] = 3
if "cfg_aisle_w" not in st.session_state:
    st.session_state["cfg_aisle_w"] = 2
if "cfg_drop_dist" not in st.session_state:
    st.session_state["cfg_drop_dist"] = 1
if "cfg_battery" not in st.session_state:
    st.session_state["cfg_battery"] = 100

if "warehouse_env" not in st.session_state:
    w, h = PRESET_DIMS[st.session_state["cfg_dim"]]
    init_bat = float(st.session_state["cfg_battery"]) * 100.0
    env = WarehouseEnvironment(
        num_robots=st.session_state["cfg_robots"],
        width=w,
        height=h,
        aisle_width=st.session_state["cfg_aisle_w"],
        dropoff_distance=st.session_state["cfg_drop_dist"],
        initial_battery=init_bat,
    )
    env.generate_scenario(
        min_tasks=st.session_state["cfg_packages"],
        max_tasks=st.session_state["cfg_packages"],
    )
    st.session_state["warehouse_env"] = env

env: WarehouseEnvironment = st.session_state["warehouse_env"]

if "sel_x" not in st.session_state:
    st.session_state["sel_x"] = 0
if "sel_y" not in st.session_state:
    st.session_state["sel_y"] = 0
if "play_mode" not in st.session_state:
    st.session_state["play_mode"] = "LOOP"

# Clamp selected coordinate to valid bounds
st.session_state["sel_x"] = max(0, min(env.width - 1, int(st.session_state["sel_x"])))
st.session_state["sel_y"] = max(0, min(env.height - 1, int(st.session_state["sel_y"])))

# -------------------------------------------------------------
# TWO-COLUMN LAYOUT: HERO (LEFT) + CONTROL PANEL (RIGHT)
# -------------------------------------------------------------
col_main, col_panel = st.columns([3.2, 1.0], gap="small")

step_1_clicked = False
step_10_clicked = False

# RIGHT CONTROL PANEL
with col_panel:
    st.markdown("<div class='control-panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>⚙️ Control Panel</div>", unsafe_allow_html=True)

    # 1. Simulation Mode
    mode_index = 0 if st.session_state["play_mode"] == "LOOP" else 1
    selected_mode = st.radio(
        "Mode",
        options=["LOOP", "CLOCK"],
        index=mode_index,
        horizontal=True,
        label_visibility="collapsed",
    )
    is_loop_mode = (selected_mode == "LOOP")
    st.session_state["play_mode"] = "LOOP" if is_loop_mode else "CLOCK"

    if is_loop_mode:
        tick_speed = st.slider(
            "Tick Delay",
            min_value=0.05,
            max_value=1.0,
            value=0.25,
            step=0.05,
            format="%.2fs",
        )
        st.markdown(
            "<div style='font-size:10px; color:#34d399; margin-top:-6px; margin-bottom:6px;'>● Continuous Loop Active</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-size:10px; color:#fbbf24; margin-bottom:4px;'>⏸ State Frozen (Clock Mode)</div>",
            unsafe_allow_html=True,
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("▶ Step", use_container_width=True):
                step_1_clicked = True
        with col_s2:
            if st.button("⏩ Step 10", use_container_width=True):
                step_10_clicked = True

    st.markdown("<hr style='border:0; border-top:1px solid #1f2937; margin:6px 0;'>", unsafe_allow_html=True)

    # 2. Dynamic Scenario Generator
    col_sc1, col_sc2 = st.columns([1.6, 1.0])
    with col_sc1:
        if st.button("🎲 New Scenario", use_container_width=True):
            env.generate_scenario(
                min_tasks=st.session_state["cfg_packages"],
                max_tasks=st.session_state["cfg_packages"],
            )
            st.rerun()
    with col_sc2:
        active_cnt = len([
            t for tid in env.current_scenario_task_ids
            if (t := env.warehouse.tasks.get(tid)) is not None and not t.is_finished()
        ])
        st.markdown(
            f"<div style='font-size:10px; color:#94a3b8; text-align:right; padding-top:4px;'><b style='color:#38bdf8;'>{active_cnt} active</b></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border:0; border-top:1px solid #1f2937; margin:6px 0;'>", unsafe_allow_html=True)

    # 3. Warehouse Geometry & Scale Settings (Collapsible or compact)
    with st.expander("🏗️ WAREHOUSE CONFIG", expanded=False):
        chosen_dim = st.selectbox(
            "Dimensions",
            options=list(PRESET_DIMS.keys()),
            index=list(PRESET_DIMS.keys()).index(st.session_state["cfg_dim"]),
        )
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            num_r = st.number_input("Robots (N)", min_value=1, max_value=20, value=int(st.session_state["cfg_robots"]), step=1)
        with c_p2:
            num_p = st.number_input("Packages (M)", min_value=1, max_value=10, value=int(st.session_state["cfg_packages"]), step=1)

        c_p3, c_p4 = st.columns(2)
        with c_p3:
            aw = st.number_input("Aisle Width", min_value=1, max_value=3, value=int(st.session_state["cfg_aisle_w"]), step=1)
        with c_p4:
            dd = st.number_input("Dropoff Dist", min_value=1, max_value=4, value=int(st.session_state["cfg_drop_dist"]), step=1)

        bat_pct = st.slider("Start Battery %", min_value=10, max_value=100, value=int(st.session_state["cfg_battery"]), step=10)

        if st.button("Apply Layout", use_container_width=True, type="primary"):
            st.session_state["cfg_dim"] = chosen_dim
            st.session_state["cfg_robots"] = num_r
            st.session_state["cfg_packages"] = num_p
            st.session_state["cfg_aisle_w"] = aw
            st.session_state["cfg_drop_dist"] = dd
            st.session_state["cfg_battery"] = bat_pct

            w, h = PRESET_DIMS[chosen_dim]
            env = WarehouseEnvironment(
                num_robots=num_r,
                width=w,
                height=h,
                aisle_width=aw,
                dropoff_distance=dd,
                initial_battery=float(bat_pct) * 100.0,
            )
            env.generate_scenario(min_tasks=num_p, max_tasks=num_p)
            st.session_state["warehouse_env"] = env
            st.session_state["sel_x"] = 0
            st.session_state["sel_y"] = 0
            st.rerun()

    st.markdown("<hr style='border:0; border-top:1px solid #1f2937; margin:6px 0;'>", unsafe_allow_html=True)

    # 4. Matrix Coordinate Controls & Keyboard Reticle
    st.markdown("<div style='font-size:11px; font-weight:700; color:#e2e8f0; margin-bottom:2px;'>🎯 RETICLE & COORDINATES</div>", unsafe_allow_html=True)

    c_x, c_y = st.columns(2)
    with c_x:
        sel_x = st.number_input(
            f"X (0-{env.width - 1})",
            min_value=0,
            max_value=env.width - 1,
            value=int(st.session_state["sel_x"]),
            step=1,
            key="side_num_x",
        )
    with c_y:
        sel_y = st.number_input(
            f"Y (0-{env.height - 1})",
            min_value=0,
            max_value=env.height - 1,
            value=int(st.session_state["sel_y"]),
            step=1,
            key="side_num_y",
        )

    st.session_state["sel_x"] = sel_x
    st.session_state["sel_y"] = sel_y
    selected_coord = (int(sel_x), int(sel_y))

    # Quick Directional Reticle D-Pad
    dp_l, dp_u, dp_d, dp_r = st.columns(4)
    with dp_l:
        if st.button("⬅️", use_container_width=True):
            st.session_state["sel_x"] = max(0, int(sel_x) - 1)
            st.rerun()
    with dp_u:
        if st.button("⬆️", use_container_width=True):
            st.session_state["sel_y"] = max(0, int(sel_y) - 1)
            st.rerun()
    with dp_d:
        if st.button("⬇️", use_container_width=True):
            st.session_state["sel_y"] = min(env.height - 1, int(sel_y) + 1)
            st.rerun()
    with dp_r:
        if st.button("➡️", use_container_width=True):
            st.session_state["sel_x"] = min(env.width - 1, int(sel_x) + 1)
            st.rerun()

    status_type, status_desc = env.check_cell_status(selected_coord)
    if selected_coord in env.charging_stations:
        status_type = "CHARGER"
    badge_class = {
        "AVAILABLE": "status-available",
        "RACK": "status-rack",
        "EXISTING_OBSTACLE": "status-obstacle",
        "DROPOFF": "status-dropoff",
        "CHARGER": "status-charger",
        "WOULD_BLOCK_DROPOFF": "status-blocked",
        "OCCUPIED_BY_ROBOT": "status-blocked",
    }.get(status_type, "status-rack")

    st.markdown(
        f"<div style='margin-bottom: 6px; font-size: 11px;'>"
        f"<span style='color:#94a3b8;'>Cell ({selected_coord[0]}, {selected_coord[1]}):</span> "
        f"<span class='status-badge {badge_class}'>{status_type.replace('_', ' ')}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    btn_place, btn_remove, btn_task = st.columns(3)
    with btn_place:
        if st.button("Place Obs", use_container_width=True):
            success, msg = env.add_custom_obstacle(selected_coord)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with btn_remove:
        if st.button("Del Obs", use_container_width=True):
            if env.remove_custom_obstacle(selected_coord):
                st.success(f"Removed at {selected_coord}")
                st.rerun()
            else:
                st.warning(f"No obstacle at {selected_coord}")
    with btn_task:
        if st.button("Add Task", use_container_width=True):
            try:
                env.spawn_task(selected_coord)
                st.success(f"Task at {selected_coord}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    if env.custom_obstacles:
        chips_html = "".join(f"<span class='obs-chip'>({ox},{oy})</span>" for ox, oy in sorted(env.custom_obstacles))
        st.markdown(
            f"<div style='font-size:10px; color:#94a3b8; margin-top:4px;'>Placed:</div><div class='chip-container'>{chips_html}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border:0; border-top:1px solid #1f2937; margin:6px 0;'>", unsafe_allow_html=True)

    # 5. Reset All
    if st.button("🔄 Reset All", use_container_width=True, type="secondary"):
        env.reset()
        st.session_state["sel_x"] = 0
        st.session_state["sel_y"] = 0
        env.generate_scenario(
            min_tasks=st.session_state["cfg_packages"],
            max_tasks=st.session_state["cfg_packages"],
        )
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# CLOCK STEPPING DISPATCH
# -------------------------------------------------------------
if not is_loop_mode:
    if step_1_clicked:
        env.step()
        if env.is_scenario_finished():
            env.generate_scenario(
                min_tasks=st.session_state["cfg_packages"],
                max_tasks=st.session_state["cfg_packages"],
            )
        st.rerun()
    elif step_10_clicked:
        for _ in range(10):
            env.step()
            if env.is_scenario_finished():
                env.generate_scenario(
                    min_tasks=st.session_state["cfg_packages"],
                    max_tasks=st.session_state["cfg_packages"],
                )
                break
        st.rerun()

# -------------------------------------------------------------
# EXTRACT SNAPSHOT & METRICS
# -------------------------------------------------------------
raw_snapshot = env.get_snapshot()
raw_snapshot["selected_cell"] = selected_coord
normalized = normalize_snapshot(raw_snapshot)
metrics = normalized.metrics

# LEFT HERO MAIN VISUALIZATION
with col_main:
    # 1. Header Bar
    sim_step = normalized.timestep or 0
    sim_time = normalized.time or 0.0
    mode_badge_html = (
        "<span class='badge-loop'>● LOOP (RUNNING)</span>"
        if is_loop_mode
        else "<span class='badge-clock'>⏸ CLOCK (PAUSED)</span>"
    )

    st.markdown(
        f"""
        <div class='header-bar'>
            <div class='header-title'>ACE — AMR Collision Avoidance & Warehouse Optimization</div>
            <div class='header-badge'>DIM: {env.width}x{env.height} | TIME: {sim_time:.1f}s | STEP: {sim_step} | {mode_badge_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Exactly Four Primary Aligned KPI Cards
    kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)

    total_tasks = metrics.total_tasks or len(env.current_scenario_task_ids) or len(normalized.tasks) or 1
    tasks_str = f"{min(metrics.tasks_completed, total_tasks)} / {total_tasks}"
    progress_pct = max(0.0, min(100.0, (metrics.tasks_completed / total_tasks) * 100.0))
    active_tasks = sum(
        1 for tid in env.current_scenario_task_ids
        if (task := env.warehouse.tasks.get(tid)) is not None and not task.is_finished()
    )

    with kpi_c1:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Tasks Completed</div><div class='kpi-value'>{tasks_str}</div></div>",
            unsafe_allow_html=True,
        )

    with kpi_c2:
        col_color = "#ef4444" if metrics.collisions > 0 else "#10b981"
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Collisions</div><div class='kpi-value' style='color:{col_color};'>{metrics.collisions}</div></div>",
            unsafe_allow_html=True,
        )

    with kpi_c3:
        dl_color = "#ef4444" if metrics.deadlocks > 0 else "#10b981"
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Deadlocks</div><div class='kpi-value' style='color:{dl_color};'>{metrics.deadlocks}</div></div>",
            unsafe_allow_html=True,
        )

    with kpi_c4:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>Replans</div><div class='kpi-value'>{metrics.replanning_count}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div class='mission-strip'><span class='live-dot'></span><b style='color:#e2e8f0;'>SCENARIO {normalized.comparison.scenario_id if normalized.comparison else env.current_scenario_id}</b>"
        f"<span>{min(metrics.tasks_completed,total_tasks)}/{total_tasks} delivered</span><div class='mission-progress'><span style='width:{progress_pct:.1f}%'></span></div>"
        f"<span>{active_tasks} active</span><span>T+{sim_time:.1f}s</span></div>",
        unsafe_allow_html=True,
    )

    # 3. Main Hero Visual: Centered Warehouse Floor with Reticle
    st.markdown("<div class='warehouse-wrapper'>", unsafe_allow_html=True)
    svg_code = SvgWarehouseRenderer.render_svg(
        normalized,
        shelves=set(env.shelf_blocks),
        custom_obstacles=set(env.custom_obstacles),
        dropoff_cells=env.dropoff_cells,
        selected_cell=selected_coord,
    )
    st.markdown(svg_code, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 4. Clean Legend Row
    st.markdown(
        """
        <div class='legend-row'>
            <span class='legend-item'><span style='color:#10b981; font-size:14px;'>●</span> Moving</span>
            <span class='legend-item'><span style='color:#f59e0b; font-size:14px;'>●</span> Waiting</span>
            <span class='legend-item'><span style='color:#ef4444; font-size:14px;'>●</span> Conflict</span>
            <span class='legend-item'><span style='color:#3b82f6; font-size:14px;'>●</span> Charging</span>
            <span class='legend-item'><span style='color:#94a3b8; font-size:14px;'>●</span> Idle</span>
            <span style='color:#334155;'>|</span>
            <span class='legend-item'><span style='background:#1e3a8a; border:1px solid #3b82f6; border-radius:3px; padding:1px 5px; font-size:10px; color:#bfdbfe; font-weight:bold;'>P</span> Pickup</span>
            <span class='legend-item'><span style='background:#064e3b; border:1px solid #10b981; border-radius:3px; padding:1px 5px; font-size:10px; color:#a7f3d0; font-weight:bold;'>D</span> Dropoff</span>
            <span class='legend-item'><span style='border:1px solid #38bdf8; border-radius:3px; padding:1px 5px; font-size:10px; color:#38bdf8;'>⚡</span> Charger</span>
            <span class='legend-item'><span style='background:#1e293b; border:1px solid #475569; border-radius:3px; padding:1px 5px; font-size:10px; color:#94a3b8;'>RACK</span></span>
            <span class='legend-item'><span style='background:#7c2d12; border:1px solid #ea580c; border-radius:3px; padding:1px 5px; font-size:10px; color:#ffffff;'>⚠️</span> Obstacle</span>
            <span class='legend-item'><span style='border:1.5px dashed #38bdf8; border-radius:3px; padding:1px 5px; font-size:10px; color:#38bdf8;'>⛶</span> Reticle</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Robot Status Cards
    ROBOT_PATH_COLORS = ["#38bdf8", "#c084fc", "#34d399", "#fbbf24", "#f472b6"]
    num_r_cards = len(normalized.robots)
    r_cols = st.columns(min(6, num_r_cards)) if num_r_cards > 0 else []
    for idx, r in enumerate(normalized.robots):
        col = r_cols[idx % len(r_cols)]
        color = ROBOT_PATH_COLORS[idx % len(ROBOT_PATH_COLORS)]
        availability = (r.availability_state or "UNKNOWN").upper()
        raw_status = (r.status or "UNKNOWN").upper()
        critical_states = {"DISCHARGED", "OFFLINE", "GOING_TO_CHARGER", "CHARGING", "LOW_BATTERY"}
        st_upper = availability if availability in critical_states else raw_status
        if st_upper in {"UNKNOWN", "ONLINE", "PLANNING"}:
            st_upper = raw_status if raw_status not in {"UNKNOWN", "ONLINE", "PLANNING"} else availability
        st_color = {
            "MOVING": "#10b981",
            "WAITING": "#f59e0b",
            "CONFLICT": "#ef4444",
            "CHARGING": "#3b82f6",
            "LOW_BATTERY": "#ef4444",
            "IDLE": "#94a3b8",
        }.get(st_upper, "#94a3b8")

        pkg_badge = "📦 Loaded" if r.has_package else "⚪ Empty"
        stage_str = r.task_stage.replace("_", " ")
        if r.battery_percentage is not None:
            bat_display = f"{r.battery_percentage:.0f}%"
        elif r.battery is not None:
            bat_display = f"{r.battery:.0f}"
        else:
            bat_display = "N/A"

        with col:
            st.markdown(
                f"""
                <div class='robot-card'>
                    <div class='robot-title'>
                        <span style='color:{color}; font-weight:bold;'>AMR {r.robot_id}</span>
                        <span style='color:{st_color}; font-size:10px; font-weight:bold;'>● {st_upper}</span>
                    </div>
                    <div style='color:#94a3b8; font-size:10px; margin-bottom:1px;'>
                        Pos: ({r.position[0]}, {r.position[1]}) | Bat: {bat_display}
                    </div>
                    <div style='color:#94a3b8; font-size:10px;'>
                        {pkg_badge} | {stage_str}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 6. ACE vs Baseline Performance Comparison Card
    comp = normalized.comparison
    if comp is not None:
        ace_t = comp.ace_time
        base_t = comp.baseline_time
        imp = comp.improvement_percentage
        finished = bool(normalized.scenario_finished)
        if finished:
            imp_color = "#10b981" if imp >= 0 else "#ef4444"
            imp_sign = "+" if imp >= 0 else ""
            performance_text = f"{imp_sign}{imp:.1f}% {'FASTER' if imp >= 0 else 'SLOWER'}"
            status_text = f"Final improvement: <b style='color:{imp_color};'>{imp_sign}{imp:.1f}%</b>"
        else:
            imp_color = "#f59e0b"
            performance_text = "● LIVE RUN"
            status_text = "Final improvement: <b style='color:#f59e0b;'>pending until scenario completes</b>"

        st.markdown(
            f"""
            <div class='benchmark-card'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div style='font-size:12px; font-weight:700; color:#e2e8f0;'>
                        ⚡ ACE vs Stop-and-Wait Baseline Benchmark (Scenario #{comp.scenario_id})
                    </div>
                    <div style='font-size:13px; font-weight:800; color:{imp_color}; font-family:ui-monospace,monospace;'>
                        {performance_text}
                    </div>
                </div>
                <div style='display:flex; gap:16px; margin-top:6px; font-size:11px; color:#94a3b8;'>
                    <div>ACE {'Completion' if finished else 'Elapsed'}: <b style='color:#38bdf8;'>{ace_t:.2f}s</b> ({comp.ace_collisions} coll)</div>
                    <div>Baseline Completion: <b style='color:#f59e0b;'>{base_t:.2f}s</b> ({comp.baseline_collisions} coll)</div>
                    <div>{status_text}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -------------------------------------------------------------
# CONTINUOUS LOOP EXECUTION
# -------------------------------------------------------------
if is_loop_mode:
    time.sleep(tick_speed)
    env.step()
    if env.is_scenario_finished():
        env.generate_scenario(
            min_tasks=st.session_state["cfg_packages"],
            max_tasks=st.session_state["cfg_packages"],
        )
    st.rerun()