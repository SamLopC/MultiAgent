import heapq
import pygame
from config import COLLISION_COLOR, CELL_SIZE, GRID_SIZE

class Car:
    def __init__(self, start, target, color):
        self.start = start
        self.target = target
        self.position = start
        self.path = []
        self.visited_positions = [self.position]  # Keep track of positions visited
        self.collided = False
        self.active = True
        self.priority = 1  # Lower number means higher priority
        self.color = color  # Car color
        self.path_color = color  # Path color is the same as car color

    def a_star(self, grid, avoid_positions=set()):
        """Implements an advanced A* algorithm for pathfinding."""
        def heuristic(a, b):
            # Manhattan distance
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

        # If we exit the loop without finding a path
        return []

    def breadth_first_search(self, grid, avoid_positions=set()):
        """Implements a Breadth-First Search (BFS) for pathfinding."""
        from collections import deque
        start = self.position
        target = self.target

        queue = deque([start])
        came_from = {start: None}
        visited = set([start])

        while queue:
            current = queue.popleft()
            if current == target:
                return self.reconstruct_path(came_from)

            for neighbor in self.get_neighbors(current, grid, avoid_positions):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    queue.append(neighbor)

        # No path found
        return []

    def dijkstra(self, grid, avoid_positions=set()):
        """Implements Dijkstra's algorithm for pathfinding."""
        start = self.position
        target = self.target

        distances = {start: 0}
        came_from = {}
        visited = set()
        pq = [(0, start)]  # (distance, node)

        while pq:
            dist, current = heapq.heappop(pq)

            if current == target:
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

        # No path found
        return []

    def reconstruct_path(self, came_from):
        """Reconstructs the path from the search algorithms."""
        path = [self.target]
        current = self.target
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path[1:]  # Exclude the starting position

    def get_neighbors(self, node, grid, avoid_positions):
        """Returns neighbors for a given node considering grid boundaries and avoidance."""
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        neighbors = []
        for d in directions:
            neighbor = (node[0] + d[0], node[1] + d[1])
            if (
                0 <= neighbor[0] < GRID_SIZE
                and 0 <= neighbor[1] < GRID_SIZE
                and grid[neighbor[1]][neighbor[0]] != -1  # Not blocked by obstacle
                and neighbor not in avoid_positions  # Avoid collision positions
            ):
                neighbors.append(neighbor)
        return neighbors

    def move(self, shared_state):
        """Moves the car step by step along its path."""
        if not self.active:
            return

        # If the car has reached its target
        if self.position == self.target:
            shared_state.update_cell(self.position, None)  # Remove car from grid
            self.active = False
            self.collided = False
            print(f"Car at {self.position} has reached its target.")
            return

        # Move to the next position in the path if available
        if self.path:
            next_position = self.path.pop(0)

            # Check if the next position is free and safe
            if shared_state.is_cell_free(next_position):
                shared_state.update_cell(self.position, next_position)  # Update shared state
                self.position = next_position
                self.visited_positions.append(self.position)  # Record the new position
                self.collided = False
            else:
                # If blocked, recompute the path dynamically using A*, then BFS, then Dijkstra
                avoid_positions = shared_state.get_occupied_positions()
                self.path = self.a_star(shared_state.grid, avoid_positions)
                if not self.path:
                    self.path = self.breadth_first_search(shared_state.grid, avoid_positions)
                if not self.path:
                    self.path = self.dijkstra(shared_state.grid, avoid_positions)

                if not self.path:
                    print(f"Car at {self.position} cannot find a path to the target.")
                    self.collided = True  # Mark as stuck
        else:
            # No path available, attempt recalculation
            avoid_positions = shared_state.get_occupied_positions()
            self.path = self.a_star(shared_state.grid, avoid_positions)
            if not self.path:
                self.path = self.breadth_first_search(shared_state.grid, avoid_positions)
            if not self.path:
                self.path = self.dijkstra(shared_state.grid, avoid_positions)

            if not self.path:
                # Still no path, mark as stuck
                print(f"Car at {self.position} cannot find a path to the target after recalculation.")
                self.collided = True

    def draw(self, screen):
        """Draws the car's movement and its current position on the grid."""
        if not self.active:
            return  # Don't draw inactive cars

        # Draw the visited positions (trail of the car)
        for pos in self.visited_positions:
            pygame.draw.rect(
                screen,
                self.path_color,
                (
                    pos[0] * CELL_SIZE + CELL_SIZE // 4,
                    pos[1] * CELL_SIZE + CELL_SIZE // 4,
                    CELL_SIZE // 2,
                    CELL_SIZE // 2,
                ),
            )

        # Draw the car's current position (highlighted)
        color = COLLISION_COLOR if self.collided else self.color
        pygame.draw.rect(
            screen,
            color,
            (
                self.position[0] * CELL_SIZE,
                self.position[1] * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            ),
        )
