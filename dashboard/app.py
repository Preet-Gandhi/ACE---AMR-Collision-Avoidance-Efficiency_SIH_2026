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
        padding-left: 1.0rem !important;
        padding-right: 1.0rem !important;
        max-width: 1440px;
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
    .robot-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 11px;
    }
    .robot-title {
        font-weight: 700;
        font-size: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 3px;
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
    }
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
        gap: 12px;
        font-size: 11px;
        color: #94a3b8;
        margin-top: 2px;
        margin-bottom: 8px;
        flex-wrap: wrap;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 5px;
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
        padding: 3px 8px !important;
        min-height: 28px !important;
        font-size: 11px !important;
    }
    div[data-testid="stNumberInput"] input {
        padding: 2px 6px !important;
        font-size: 12px !important;
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

# Initialize simulation environment in session state
if "warehouse_env" not in st.session_state:
    env = WarehouseEnvironment(num_robots=3)
    env.generate_scenario()
    st.session_state["warehouse_env"] = env

env: WarehouseEnvironment = st.session_state["warehouse_env"]

# Track selected coordinates for obstacle interaction
if "sel_x" not in st.session_state:
    st.session_state["sel_x"] = 0
if "sel_y" not in st.session_state:
    st.session_state["sel_y"] = 0

# Track play mode
if "play_mode" not in st.session_state:
    st.session_state["play_mode"] = "LOOP"

# -------------------------------------------------------------
# TWO-COLUMN LAYOUT: HERO (LEFT) + CONTROL PANEL (RIGHT)
# -------------------------------------------------------------
col_main, col_panel = st.columns([3.1, 1.1], gap="medium")

# Clock mode step triggers
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
        help="LOOP: continuous dynamic scenario execution. CLOCK: frozen state for manual inspection and stepping.",
    )
    is_loop_mode = (selected_mode == "LOOP")
    st.session_state["play_mode"] = "LOOP" if is_loop_mode else "CLOCK"

    if is_loop_mode:
        tick_speed = st.slider(
            "Tick Delay",
            min_value=0.05,
            max_value=1.0,
            value=0.3,
            step=0.05,
            format="%.2fs",
        )
        st.markdown(
            "<div style='font-size:11px; color:#34d399; margin-top:-6px; margin-bottom:8px;'>● Continuous Loop Active</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-size:11px; color:#fbbf24; margin-bottom:6px;'>⏸ State Frozen (Clock Mode)</div>",
            unsafe_allow_html=True,
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("▶ Step", use_container_width=True):
                step_1_clicked = True
        with col_s2:
            if st.button("⏩ Step 10", use_container_width=True):
                step_10_clicked = True

    st.markdown("<hr style='border:0; border-top:1px solid #1f2937; margin:8px 0;'>", unsafe_allow_html=True)

    # 2. Dynamic Scenarios
    if st.button("🎲 New Scenario", use_container_width=True):
        env.generate_scenario()
        st.rerun()

    active_tasks = [t for t in env.warehouse.tasks.values() if not t.is_finished()]
    st.markdown(
        f"<div style='font-size:11px; color:#94a3b8; margin-top:2px;'>Active Tasks: <b style='color:#38bdf8;'>{len(active_tasks)} pending</b></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='border:0; border-top:1px solid #1f2937; margin:8px 0;'>", unsafe_allow_html=True)

    # 3. Matrix Coordinate Controls (Obstacles & Tasks)
    st.markdown("<div style='font-size:11px; font-weight:700; color:#e2e8f0; margin-bottom:4px;'>🎯 COORDINATE CONTROLS</div>", unsafe_allow_html=True)

    c_x, c_y = st.columns(2)
    with c_x:
        sel_x = st.number_input(
            "X (0-13)",
            min_value=0,
            max_value=env.WIDTH - 1,
            value=int(st.session_state["sel_x"]),
            step=1,
            key="side_num_x",
        )
    with c_y:
        sel_y = st.number_input(
            "Y (0-9)",
            min_value=0,
            max_value=env.HEIGHT - 1,
            value=int(st.session_state["sel_y"]),
            step=1,
            key="side_num_y",
        )

    st.session_state["sel_x"] = sel_x
    st.session_state["sel_y"] = sel_y
    selected_coord = (int(sel_x), int(sel_y))

    status_type, status_desc = env.check_cell_status(selected_coord)
    badge_class = {
        "AVAILABLE": "status-available",
        "RACK": "status-rack",
        "EXISTING_OBSTACLE": "status-obstacle",
        "DROPOFF": "status-dropoff",
        "WOULD_BLOCK_DROPOFF": "status-blocked",
        "OCCUPIED_BY_ROBOT": "status-blocked",
    }.get(status_type, "status-rack")

    st.markdown(
        f"<div style='margin-bottom: 8px; font-size: 11px;'>"
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
            f"<div style='font-size:11px; color:#94a3b8; margin-top:6px;'>Placed:</div><div class='chip-container'>{chips_html}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border:0; border-top:1px solid #1f2937; margin:8px 0;'>", unsafe_allow_html=True)

    # 4. Reset All
    if st.button("🔄 Reset All", use_container_width=True, type="secondary"):
        env.reset()
        st.session_state["sel_x"] = 0
        st.session_state["sel_y"] = 0
        env.generate_scenario()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# CLOCK STEPPING DISPATCH
# -------------------------------------------------------------
if not is_loop_mode:
    if step_1_clicked:
        env.step()
        if env.is_scenario_finished():
            env.generate_scenario()
        st.rerun()
    elif step_10_clicked:
        for _ in range(10):
            env.step()
            if env.is_scenario_finished():
                env.generate_scenario()
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
            <div class='header-title'>ACE — AMR Collision Avoidance</div>
            <div class='header-badge'>SIM TIME: {sim_time:.1f}s | STEP: {sim_step} | {mode_badge_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Exactly Four Aligned KPI Cards
    kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)

    total_tasks = metrics.total_tasks or len(normalized.tasks) or len(env.warehouse.tasks) or 1
    tasks_str = f"{metrics.tasks_completed} / {total_tasks}"

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

    # 3. Main Hero Visual: Centered Warehouse Floor with Reticle
    st.markdown("<div class='warehouse-wrapper'>", unsafe_allow_html=True)
    svg_code = SvgWarehouseRenderer.render_svg(
        normalized,
        shelves=set(env.SHELF_BLOCKS),
        custom_obstacles=set(env.custom_obstacles),
        dropoff_cells=env.DROPOFF_CELLS,
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
            <span class='legend-item'><span style='color:#94a3b8; font-size:14px;'>●</span> Idle</span>
            <span style='color:#334155;'>|</span>
            <span class='legend-item'><span style='background:#1e3a8a; border:1px solid #3b82f6; border-radius:3px; padding:1px 5px; font-size:10px; color:#bfdbfe; font-weight:bold;'>P</span> Rack Pickup</span>
            <span class='legend-item'><span style='background:#064e3b; border:1px solid #10b981; border-radius:3px; padding:1px 5px; font-size:10px; color:#a7f3d0; font-weight:bold;'>D</span> Active Dropoff</span>
            <span class='legend-item'><span style='background:#1e293b; border:1px solid #475569; border-radius:3px; padding:1px 6px; font-size:10px; color:#94a3b8;'>RACK</span> Shelf</span>
            <span class='legend-item'><span style='background:#7c2d12; border:1px solid #ea580c; border-radius:3px; padding:1px 5px; font-size:10px; color:#ffffff;'>⚠️</span> Obstacle</span>
            <span class='legend-item'><span style='border:1.5px dashed #38bdf8; border-radius:3px; padding:1px 5px; font-size:10px; color:#38bdf8;'>⛶</span> Reticle</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Robot Status Cards
    ROBOT_PATH_COLORS = ["#38bdf8", "#c084fc", "#34d399", "#fbbf24", "#f472b6"]
    r_cols = st.columns(len(normalized.robots))
    for idx, (col, r) in enumerate(zip(r_cols, normalized.robots)):
        color = ROBOT_PATH_COLORS[idx % len(ROBOT_PATH_COLORS)]
        st_color = {
            "MOVING": "#10b981",
            "WAITING": "#f59e0b",
            "CONFLICT": "#ef4444",
            "IDLE": "#94a3b8",
        }.get(r.status.upper(), "#94a3b8")

        pkg_badge = "📦 Loaded" if r.has_package else "⚪ Empty"
        stage_str = r.task_stage.replace("_", " ")

        with col:
            st.markdown(
                f"""
                <div class='robot-card'>
                    <div class='robot-title'>
                        <span style='color:{color}; font-weight:bold;'>AMR {r.robot_id}</span>
                        <span style='color:{st_color}; font-size:11px; font-weight:bold;'>● {r.status}</span>
                    </div>
                    <div style='color:#94a3b8; font-size:11px; margin-bottom:2px;'>
                        Pos: <span style='color:#e2e8f0; font-family:ui-monospace,monospace;'>({r.position[0]}, {r.position[1]})</span> | {pkg_badge}
                    </div>
                    <div style='color:#94a3b8; font-size:11px;'>
                        Stage: <span style='color:#38bdf8; font-weight:600;'>{stage_str}</span>
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
        env.generate_scenario()
    st.rerun()
