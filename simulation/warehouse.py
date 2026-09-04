from auction.task import Task


class Warehouse:
    def __init__(self, grid):
        if isinstance(grid, tuple):
            width, height = grid
            self.width, self.height = width, height
            self.static_obstacles = set()
        else:
            self.height, self.width = len(grid), len(grid[0])
            self.static_obstacles = {(x, y) for y, row in enumerate(grid) for x, cell in enumerate(row) if cell in (1, "#", "X")}
        self.dynamic_obstacles = set()
        self.tasks: dict[int, Task] = {}

    def is_valid_position(self, position):
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, position):
        return self.is_valid_position(position) and position not in self.static_obstacles | self.dynamic_obstacles

    def get_neighbors(self, position):
        x, y = position
        candidates = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        return [p for p in candidates if self.is_walkable(p)]

    def add_obstacle(self, position):
        if not self.is_valid_position(position): raise ValueError("obstacle is outside warehouse")
        self.dynamic_obstacles.add(tuple(position))
    def remove_obstacle(self, position): self.dynamic_obstacles.discard(tuple(position))
    def add_task(self, task): self.tasks[task.task_id] = task
    def remove_task(self, task_id): return self.tasks.pop(task_id, None)
    def get_pending_tasks(self): return [t for t in self.tasks.values() if t.is_available()]
    def get_task(self, task_id): return self.tasks.get(task_id)
