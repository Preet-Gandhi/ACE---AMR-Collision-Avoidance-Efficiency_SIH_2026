from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.metrics import Metrics
from simulation.simulator import Simulator
from simulation.warehouse import Warehouse


def build_world(size=(9, 9), starts=()):
    warehouse = Warehouse(size)
    network, reservations, metrics = Network(), ReservationTable(), Metrics()
    planner = AStarPlanner(warehouse)
    robots = [Robot(robot_id, position, warehouse, planner, network, reservations) for robot_id, position in starts]
    return Simulator(warehouse, robots, network, reservations, metrics), robots
