import math


class CollisionDetector:

    def distance(self, robot_a, robot_b):
        return math.dist(
            robot_a.state.position,
            robot_b.state.position,
        )

    def detect_collision(
        self,
        robot_a,
        robot_b,
        threshold=0.0,
    ):
        return (
            self.distance(robot_a, robot_b)
            <= threshold
        )

    def detect_all_collisions(
        self,
        robots,
        threshold=0.0,
    ):
        collisions = []

        for i, robot_a in enumerate(robots):
            for robot_b in robots[i + 1:]:
                if self.detect_collision(
                    robot_a,
                    robot_b,
                    threshold,
                ):
                    collisions.append(
                        (
                            robot_a,
                            robot_b,
                        )
                    )

        return collisions

    @staticmethod
    def _at(path, timestep):
        if not path:
            return None

        return path[
            min(
                timestep,
                len(path) - 1,
            )
        ]

    def detect_vertex_conflict(
        self,
        path_a,
        path_b,
        horizon=None,
    ):
        if not path_a or not path_b:
            return False

        if horizon is None:
            horizon = max(
                len(path_a),
                len(path_b),
            )

        for timestep in range(horizon):
            if (
                self._at(path_a, timestep)
                == self._at(path_b, timestep)
            ):
                return True

        return False

    def detect_edge_conflict(
        self,
        path_a,
        path_b,
        horizon=None,
    ):
        if not path_a or not path_b:
            return False

        if horizon is None:
            horizon = max(
                len(path_a),
                len(path_b),
            )

        for timestep in range(1, horizon):
            a_previous = self._at(
                path_a,
                timestep - 1,
            )

            a_current = self._at(
                path_a,
                timestep,
            )

            b_previous = self._at(
                path_b,
                timestep - 1,
            )

            b_current = self._at(
                path_b,
                timestep,
            )

            if (
                a_previous == b_current
                and b_previous == a_current
                and a_previous != a_current
            ):
                return True

        return False

    def detect_future_conflict(
        self,
        path_a,
        path_b,
        horizon=None,
    ):
        return (
            self.detect_vertex_conflict(
                path_a,
                path_b,
                horizon,
            )
            or
            self.detect_edge_conflict(
                path_a,
                path_b,
                horizon,
            )
        )

    def predict_collision(
        self,
        robot_a,
        robot_b,
        horizon,
    ):
        path_a = (
            [robot_a.state.position]
            +
            robot_a.state.path[
                robot_a.state.path_index:
            ]
        )

        path_b = (
            [robot_b.state.position]
            +
            robot_b.state.path[
                robot_b.state.path_index:
            ]
        )

        return self.detect_future_conflict(
            path_a,
            path_b,
            horizon,
        )

    def detect_all_path_conflicts(
        self,
        robots,
        horizon=None,
    ):
        conflicts = []

        for index, robot_a in enumerate(robots):
            path_a = (
                [robot_a.state.position]
                +
                robot_a.state.path[
                    robot_a.state.path_index:
                ]
            )

            for robot_b in robots[index + 1:]:
                path_b = (
                    [robot_b.state.position]
                    +
                    robot_b.state.path[
                        robot_b.state.path_index:
                    ]
                )

                if self.detect_future_conflict(
                    path_a,
                    path_b,
                    horizon,
                ):
                    conflicts.append(
                        (
                            robot_a,
                            robot_b,
                        )
                    )

        return conflicts