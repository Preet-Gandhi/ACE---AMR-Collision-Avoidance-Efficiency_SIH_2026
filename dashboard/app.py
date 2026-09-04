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

# Dark clean robotics styling focusing on alignment, contrast, and hierarchy
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #1f2937;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    .header-title {
        font-size: 22px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #f8fafc;
        margin: 0;
    }
    .header-badge {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        color: #94a3b8;
        font-family: ui-monospace, monospace;
    }
    .kpi-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 14px;
        text-align: center;
        height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        color: #94a3b8;
        letter-spacing: 0.8px;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 24px;
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
        border-radius: 12px;
        padding: 16px;
        margin-top: 14px;
        margin-bottom: 10px;
    }
    .legend-row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 18px;
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .control-panel {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 14px 16px;
        min-height: 220px;
    }
    .panel-title {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: #e2e8f0;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .status-badge {
        display: inline-block;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 8px;
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
        gap: 6px;
        flex-wrap: wrap;
        margin-top: 8px;
    }
    .obs-chip {
        background: #1f2937;
        border: 1px solid #ea580c;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
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
    env.randomize_pickups(count=3)
    st.session_state["warehouse_env"] = env

env: WarehouseEnvironment = st.session_state["warehouse_env"]

# Track selected coordinates for obstacle interaction
if "sel_x" not in st.session_state:
    st.session_state["sel_x"] = 0
if "sel_y" not in st.session_state:
    st.session_state["sel_y"] = 0

selected_coord = (int(st.session_state["sel_x"]), int(st.session_state["sel_y"]))

# Extract snapshot and normalize
raw_snapshot = env.get_snapshot()
raw_snapshot["selected_cell"] = selected_coord
normalized = normalize_snapshot(raw_snapshot)
metrics = normalized.metrics

# 1. Header Bar
sim_step = normalized.timestep or 0
sim_time = normalized.time or 0.0
st.markdown(
    f"""
    <div class='header-bar'>
        <div class='header-title'>ACE — AMR Collision Avoidance</div>
        <div class='header-badge'>SIM TIME: {sim_time:.1f}s | STEP: {sim_step}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 2. Four Aligned KPI Cards
kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)

total_tasks = metrics.total_tasks or len(normalized.tasks) or 3
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
        <span class='legend-item'><span style='background:#064e3b; border:1px solid #10b981; border-radius:3px; padding:1px 5px; font-size:10px; color:#a7f3d0; font-weight:bold;'>D</span> Dropoff Station</span>
        <span class='legend-item'><span style='background:#1e293b; border:1px solid #475569; border-radius:3px; padding:1px 6px; font-size:10px; color:#94a3b8;'>RACK</span> Shelf</span>
        <span class='legend-item'><span style='background:#7c2d12; border:1px solid #ea580c; border-radius:3px; padding:1px 5px; font-size:10px; color:#ffffff;'>⚠️</span> Custom Obstacle</span>
        <span class='legend-item'><span style='border:1.5px dashed #38bdf8; border-radius:3px; padding:1px 5px; font-size:10px; color:#38bdf8;'>⛶</span> Target Reticle</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# 5. Compact Aligned Controls Area
col_obs, col_tasks, col_sim = st.columns([4, 4, 3])

# Panel 1: Obstacle Placement
with col_obs:
    st.markdown("<div class='control-panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>⚠️ Obstacle Management</div>", unsafe_allow_html=True)

    # Coordinate selection
    c_x, c_y = st.columns(2)
    with c_x:
        sel_x = st.number_input("X Coordinate", min_value=0, max_value=env.WIDTH - 1, value=st.session_state["sel_x"], step=1, key="num_x")
    with c_y:
        sel_y = st.number_input("Y Coordinate", min_value=0, max_value=env.HEIGHT - 1, value=st.session_state["sel_y"], step=1, key="num_y")

    # Update session state if changed
    if sel_x != st.session_state["sel_x"] or sel_y != st.session_state["sel_y"]:
        st.session_state["sel_x"] = sel_x
        st.session_state["sel_y"] = sel_y
        st.rerun()

    active_coord = (int(sel_x), int(sel_y))
    status_type, status_desc = env.check_cell_status(active_coord)

    # Status badge styling
    badge_class = {
        "AVAILABLE": "status-available",
        "RACK": "status-rack",
        "EXISTING_OBSTACLE": "status-obstacle",
        "DROPOFF": "status-dropoff",
        "WOULD_BLOCK_DROPOFF": "status-blocked",
    }.get(status_type, "status-rack")

    st.markdown(
        f"<div style='margin-bottom: 10px; font-size: 12px;'>"
        f"<span style='color:#94a3b8;'>Target ({active_coord[0]}, {active_coord[1]}):</span> "
        f"<span class='status-badge {badge_class}'>{status_type.replace('_', ' ')}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    btn_place, btn_remove = st.columns(2)
    with btn_place:
        if st.button("Place Obstacle", use_container_width=True):
            success, msg = env.add_custom_obstacle(active_coord)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with btn_remove:
        if st.button("Remove Obstacle", use_container_width=True):
            if env.remove_custom_obstacle(active_coord):
                st.success(f"Removed obstacle at {active_coord}")
                st.rerun()
            else:
                st.warning(f"No custom obstacle at {active_coord}")

    # Active obstacles list
    if env.custom_obstacles:
        chips_html = "".join(f"<span class='obs-chip'>({ox},{oy})</span>" for ox, oy in sorted(env.custom_obstacles))
        st.markdown(f"<div style='font-size:11px; color:#94a3b8; margin-top:8px;'>Active Obstacles:</div><div class='chip-container'>{chips_html}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size:11px; color:#64748b; margin-top:8px;'>No custom obstacles placed.</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Panel 2: Pickup Tasks
with col_tasks:
    st.markdown("<div class='control-panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>📦 Task & Pickup Controls</div>", unsafe_allow_html=True)

    rack_pickups = [pos for pos in env.RACK_PICKUP_CELLS if pos not in env.custom_obstacles]
    selected_pickup = st.selectbox(
        "Rack-Facing Pickup Cell",
        options=rack_pickups,
        format_func=lambda p: f"Aisle ({p[0]}, {p[1]}) [Rack-Adjacent]",
    )

    t_btn1, t_btn2 = st.columns(2)
    with t_btn1:
        if st.button("Assign Selected", use_container_width=True):
            try:
                env.spawn_task(selected_pickup)
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with t_btn2:
        if st.button("🎲 Randomize Pickups", use_container_width=True):
            env.randomize_pickups(count=3)
            st.rerun()

    active_tasks = [t for t in env.warehouse.tasks.values() if t.status.value != "COMPLETED"]
    st.markdown(
        f"<div style='font-size:11px; color:#94a3b8; margin-top:16px;'>Active Tasks: {len(active_tasks)} pending | Common Dropoff: ({env.DROPOFF_STATION[0]}, {env.DROPOFF_STATION[1]})</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# Panel 3: Simulation & Reset
with col_sim:
    st.markdown("<div class='control-panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>⚙️ Simulation Execution</div>", unsafe_allow_html=True)

    sim_b1, sim_b2 = st.columns(2)
    with sim_b1:
        if st.button("▶ Step Clock", use_container_width=True):
            env.step()
            st.rerun()
    with sim_b2:
        if st.button("⏩ Step 10", use_container_width=True):
            for _ in range(10):
                env.step()
            st.rerun()

    # Robot task stage indicators
    stages_html = []
    for r in normalized.robots:
        stage = getattr(r, "task_stage", "IDLE")
        has_pkg = getattr(r, "has_package", False)
        pkg_icon = " 📦" if has_pkg else ""
        stages_html.append(f"<div style='font-size:11px; margin-top:3px;'><span style='font-weight:bold; color:#e2e8f0;'>R{r.robot_id}:</span> <span style='color:#38bdf8;'>{stage.replace('_', ' ')}{pkg_icon}</span></div>")

    st.markdown(f"<div style='margin-top: 10px; padding: 6px 8px; background:#1e293b; border-radius:4px;'>{''.join(stages_html)}</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    # Destructive reset action
    if st.button("🔄 Reset All", use_container_width=True, type="secondary"):
        env.reset()
        st.session_state["sel_x"] = 0
        st.session_state["sel_y"] = 0
        env.randomize_pickups(count=3)
        st.rerun()

    st.markdown(
        "<div style='font-size:11px; color:#64748b; margin-top:8px;'>Reset All clears custom obstacles, resets tasks, robots, and metrics.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
