import heapq
import pygame
from config import COLLISION_COLOR, CELL_SIZE, GRID_SIZE

class Car:
    def __init__(self, start, target, color, priority=1):
        self.start = start
        self.target = target
        self.position = start
        self.path = []
        self.visited_positions = [self.position]  # Keep track of positions visited
        self.collided = False
        self.active = True
        self.priority = priority
        self.color = color  # Car color
        self.path_color = color  # Path color is the same as car color

        # Simple placeholder for RL Q-values: a dictionary keyed by (state,action)
        # In a real scenario, you'd define states (like (pos, target)) and actions (move directions)
        self.q_values = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9

    def a_star(self, grid, avoid_positions=set()):
        """Implements an advanced A* algorithm for pathfinding."""
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = []
        heapq.heappush(open_set, (heuristic(self.position, self.target), self.position))
        came_from = {}
        g_score = {self.position: 0}
        closed_set = set()

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == self.target:
                return self.reconstruct_path(came_from)

            if current in closed_set:
                continue
            closed_set.add(current)

            neighbors = self.get_neighbors(current, grid, avoid_positions)

            for neighbor in neighbors:
                tentative_g_score = g_score[current] + 1

                if neighbor in closed_set:
                    continue

                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score = tentative_g_score + heuristic(neighbor, self.target)
                    heapq.heappush(open_set, (f_score, neighbor))
        return []

    def breadth_first_search(self, grid, avoid_positions=set()):
        """Breadth-First Search (BFS) for pathfinding."""
        from collections import deque
        start = self.position
        target = self.target

        queue = deque([start])
        came_from = {start: None}
        visited = {start}

        while queue:
            current = queue.popleft()
            if current == target:
                return self.reconstruct_path(came_from)

            for neighbor in self.get_neighbors(current, grid, avoid_positions):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    queue.append(neighbor)
        return []

    def dijkstra(self, grid, avoid_positions=set()):
        """Dijkstra's algorithm for pathfinding."""
        distances = {self.position: 0}
        came_from = {}
        visited = set()
        pq = [(0, self.position)]

        while pq:
            dist, current = heapq.heappop(pq)

            if current == self.target:
                return self.reconstruct_path(came_from)

            if current in visited:
                continue
            visited.add(current)

            for neighbor in self.get_neighbors(current, grid, avoid_positions):
                new_dist = dist + 1
                if new_dist < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_dist
                    came_from[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))
        return []

    def reconstruct_path(self, came_from):
        """Reconstructs the path from the search algorithms."""
        path = [self.target]
        current = self.target
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path[1:]  # Exclude starting position

    def get_neighbors(self, node, grid, avoid_positions):
        """Returns neighbors considering boundaries, obstacles, and avoided positions."""
        directions = [(0,1),(1,0),(0,-1),(-1,0)]
        neighbors = []
        for d in directions:
            neighbor = (node[0]+d[0], node[1]+d[1])
            if (
                0 <= neighbor[0] < GRID_SIZE and
                0 <= neighbor[1] < GRID_SIZE and
                grid[neighbor[1]][neighbor[0]] != -1 and
                neighbor not in avoid_positions
            ):
                neighbors.append(neighbor)
        return neighbors

    def move(self, shared_state):
        """Moves the car step by step along its path with collision avoidance and communication."""
        if not self.active:
            return

        if self.position == self.target:
            shared_state.update_cell(self.position, None)
            self.active = False
            self.collided = False
            print(f"Car at {self.position} (Priority {self.priority}) reached its target.")
            return

        if self.path:
            next_position = self.path[0]
            # Before moving, check if another car occupies or predicts this cell
            # If occupied, try communication for yielding or path adjustment
            if not shared_state.is_cell_free(next_position):
                # Communicate with the occupant to negotiate priority
                occupant = shared_state.get_car_at_position(next_position)
                if occupant and occupant.priority > self.priority:
                    # Request occupant to yield or move
                    shared_state.send_message(self, occupant, "yield_request")

                # After communication attempt, check if cell is free now
                if shared_state.is_cell_free(next_position):
                    self.execute_move(shared_state, next_position)
                else:
                    # Recalculate path using fallback methods
                    self.recalculate_path(shared_state)
            else:
                # Cell is free, just move
                self.execute_move(shared_state, next_position)
        else:
            # No path available, recalculate
            self.recalculate_path(shared_state)

    def execute_move(self, shared_state, next_position):
        """Execute the movement to the next position."""
        if shared_state.is_cell_free(next_position):
            shared_state.update_cell(self.position, next_position)
            self.position = next_position
            self.visited_positions.append(self.position)
            self.path.pop(0)
            self.collided = False
            # RL reward signal for successful move (small positive)
            self.receive_reward(0.1)
        else:
            # Cell blocked even after attempts, recalculate path
            self.recalculate_path(shared_state)

    def recalculate_path(self, shared_state):
        """Recalculate path if blocked, using A*, BFS, then Dijkstra."""
        self.collided = True  # stuck or blocked situation
        avoid_positions = shared_state.get_occupied_positions()
        self.path = self.a_star(shared_state.grid, avoid_positions)
        if not self.path:
            self.path = self.breadth_first_search(shared_state.grid, avoid_positions)
        if not self.path:
            self.path = self.dijkstra(shared_state.grid, avoid_positions)

        if not self.path:
            print(f"Car at {self.position} (Priority {self.priority}) cannot find a path to the target.")
            # RL penalty for being stuck
            self.receive_reward(-2)

    def receive_reward(self, reward):
        """Placeholder method for RL reward. In a real scenario, update Q-values or policies."""
        # For now, this method can be expanded for RL.
        # Example: Q-value updates would occur here if states/actions were tracked.
        pass

    def draw(self, screen):
        """Draws the car and its visited trail."""
        if not self.active:
            return

        # Draw visited trail
        for pos in self.visited_positions:
            pygame.draw.rect(
                screen,
                self.path_color,
                (
                    pos[0]*CELL_SIZE + CELL_SIZE//4,
                    pos[1]*CELL_SIZE + CELL_SIZE//4,
                    CELL_SIZE//2,
                    CELL_SIZE//2,
                ),
            )

        # Draw current position
        color = COLLISION_COLOR if self.collided else self.color
        pygame.draw.rect(
            screen,
            color,
            (
                self.position[0]*CELL_SIZE,
                self.position[1]*CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            ),
        )
