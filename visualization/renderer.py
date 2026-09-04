class Renderer:
    def __init__(self, warehouse=None, robots=None, metrics=None, reservation_table=None):
        self.warehouse, self.robots, self.metrics, self.reservation_table = warehouse, robots or [], metrics, reservation_table
    def render_warehouse(self, warehouse=None):
        warehouse = warehouse or self.warehouse
        return "\n".join("".join("#" if (x, y) in warehouse.static_obstacles | warehouse.dynamic_obstacles else "." for x in range(warehouse.width)) for y in range(warehouse.height))
    def render_robots(self, robots=None): return {r.robot_id: r.state.position for r in (robots or self.robots)}
    def render_tasks(self, tasks): return {t.task_id: t.status.value for t in tasks}
    def render_paths(self, robots=None): return {r.robot_id: list(r.state.path) for r in (robots or self.robots)}
    def render_reservations(self, reservation_table=None): return (reservation_table or self.reservation_table)._reservations.copy()
    def render_metrics(self, metrics=None): return (metrics or self.metrics).get_summary()
    def update(self): return {"warehouse": self.render_warehouse(), "robots": self.render_robots(), "metrics": self.render_metrics()}
