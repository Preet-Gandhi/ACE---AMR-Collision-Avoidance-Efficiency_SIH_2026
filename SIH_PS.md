# SIH Problem Statement

## Problem Statement Details

| Field                       | Details                                                                                              |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| **S.No.**                   | 123                                                                                                  |
| **Organization**            | Bharat Electronics Limited                                                                           |
| **Problem Statement ID**    | SIH26123                                                                                             |
| **Problem Statement Title** | Edge-AI Based Distributed Fleet Coordination for Autonomous Mobile Robots (AMRs) in Smart Warehouses |
| **Category**                | Software                                                                                             |
| **Theme**                   | Smart Automation                                                                                     |

---

## Problem Statement

### Background

Modern smart warehouses rely on fleets of **Autonomous Mobile Robots (AMRs)** to move goods efficiently. As fleet sizes grow, relying entirely on a centralized cloud server for path planning introduces several challenges:

* High network latency
* Vulnerability to Wi-Fi dead zones
* Single points of failure
* Delays in real-time decision-making

To address these limitations, modern robotics is shifting toward **decentralized, edge-computing solutions**, where robots can communicate directly with each other and make split-second decisions locally.

### Objective

Design a **decentralized coordination and collision-avoidance framework** for a multi-robot fleet consisting of **at least 3 AMRs** operating in a dynamic warehouse environment.

The system must run locally on edge hardware, such as **Raspberry Pi** or **Jetson Nano**, onboard each robot.

### Core Requirements

#### 1. Decentralized Communication

Implement inter-robot communication that allows robots to:

* Share their current position
* Communicate their intended paths or movements
* Exchange relevant localization information
* Operate without relying on a central server

#### 2. Dynamic Multi-Agent Conflict Resolution

The system should resolve conflicts between robots in real time, including:

* Deadlocks
* Potential collisions
* Narrow intersections
* Warehouse choke points
* Overlapping paths

#### 3. Task Allocation & Re-routing

The system should automatically adapt when the warehouse environment changes.

For example, if one robot encounters a blocked aisle, the system should be able to:

* Re-route the affected robot
* Change its path
* Re-assign pickup points when necessary
* Coordinate the remaining fleet accordingly

---

## Expected Solution

The expected solution is a **multi-robot simulation** demonstrating decentralized coordination between the AMRs.

### Decentralized Network Stack

A peer-to-peer communication protocol should allow robots to locally share:

* Position data
* Localization information
* Movement intent

The system should not depend on a centralized server for core coordination.

### Multi-Agent Path Planning

Implement suitable **multi-agent path-planning algorithms** capable of operating on edge hardware.

The planning system should account for:

* Other robots
* Dynamic obstacles
* Conflicting paths
* Deadlocks
* Narrow passages and intersections

### Fleet Dashboard

Develop a lightweight monitoring dashboard that provides real-time visibility into the fleet.

The dashboard should visualize:

* Robot positions
* Fleet activity
* Battery status

---

## Success Criteria

The solution should achieve the following:

1. **Zero inter-robot collisions**
2. **At least 20% reduction in total task completion time** compared to traditional **stop-and-wait** methods when handling overlapping paths.

---

## Additional Information

| Resource                | Link |
| ----------------------- | ---- |
| **YouTube**             | —    |
| **Dataset**             | —    |
| **Contact Information** | —    |