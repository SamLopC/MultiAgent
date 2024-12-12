import heapq
import pygame
import random
from config import COLLISION_COLOR, CELL_SIZE, GRID_SIZE

class Car:
    def __init__(self, start, target, color, priority=1, role="normal"):
        self.start = start
        self.target = target
        self.position = start
        self.path = []
        self.visited_positions = [self.position]
        self.collided = False
        self.active = True
        self.priority = priority
        self.role = role
        self.color = color
        self.path_color = color

        # RL-like parameters
        self.q_values = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.algorithms = ["a_star", "breadth_first_search", "dijkstra"]
        self.epsilon = 0.05
        self.last_state = None
        self.last_action = None

    def find_path(self, grid, avoid_positions=set()):
        state = (self.position, self.target)
        algo = self.select_algorithm(state)

        path = self.run_algorithm(algo, grid, avoid_positions)
        if not path:
            for fallback_algo in self.algorithms:
                if fallback_algo != algo:
                    path = self.run_algorithm(fallback_algo, grid, avoid_positions)
                    if path:
                        self.update_q_values(state, algo, -1)  # penalty for fail
                        self.last_state, self.last_action = state, fallback_algo
                        return path
            # total failure
            self.update_q_values(state, algo, -2)
        else:
            self.update_q_values(state, algo, 1)  # success
            self.last_state, self.last_action = state, algo
        return path

    def select_algorithm(self, state):
        if random.random() < self.epsilon:
            return random.choice(self.algorithms)
        # Exploit
        return self.best_algo_for_state(state)

    def best_algo_for_state(self, state):
        q_vals = {algo: self.q_values.get((state, algo), 0) for algo in self.algorithms}
        best = max(q_vals, key=q_vals.get)
        return best

    def update_q_values(self, state, action, reward):
        # Simple Q-learning update
        if self.last_state is not None and self.last_action is not None:
            old_q = self.q_values.get((self.last_state, self.last_action), 0)
            best_future = max([self.q_values.get((state, a), 0) for a in self.algorithms], default=0)
            new_q = old_q + self.learning_rate * (reward + self.discount_factor*best_future - old_q)
            self.q_values[(self.last_state, self.last_action)] = new_q

    def run_algorithm(self, algo, grid, avoid_positions):
        if algo == "a_star":
            return self.a_star(grid, avoid_positions)
        elif algo == "breadth_first_search":
            return self.breadth_first_search(grid, avoid_positions)
        else:
            return self.dijkstra(grid, avoid_positions)

    def a_star(self, grid, avoid_positions=set()):
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        start, target = self.position, self.target
        g_score = {start: 0}
        came_from = {}
        visited = set()
        open_set = [(heuristic(start,target), start)]

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == target:
                return self.reconstruct_path(came_from)
            if current in visited:
                continue
            visited.add(current)
            for neighbor, cost in self.get_neighbors_cost(current, grid, avoid_positions):
                tentative_g = g_score[current]+cost
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + heuristic(neighbor,target)
                    heapq.heappush(open_set, (f, neighbor))
        return []

    def breadth_first_search(self, grid, avoid_positions=set()):
        from collections import deque
        start, target = self.position, self.target
        queue = deque([start])
        came_from = {start: None}
        visited = {start}
        while queue:
            current = queue.popleft()
            if current == target:
                return self.reconstruct_path(came_from)
            for neighbor, cost in self.get_neighbors_cost(current, grid, avoid_positions):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    queue.append(neighbor)
        return []

    def dijkstra(self, grid, avoid_positions=set()):
        start, target = self.position, self.target
        distances = {start: 0}
        came_from = {}
        visited = set()
        pq = [(0,start)]
        while pq:
            dist, current = heapq.heappop(pq)
            if current == target:
                return self.reconstruct_path(came_from)
            if current in visited:
                continue
            visited.add(current)
            for neighbor, cost in self.get_neighbors_cost(current, grid, avoid_positions):
                new_dist = dist+cost
                if new_dist < distances.get(neighbor,float('inf')):
                    distances[neighbor] = new_dist
                    came_from[neighbor] = current
                    heapq.heappush(pq,(new_dist,neighbor))
        return []

    def reconstruct_path(self, came_from):
        path = [self.target]
        current = self.target
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path[1:]

    def get_neighbors_cost(self, node, grid, avoid_positions):
        directions = [(0,1),(1,0),(0,-1),(-1,0)]
        neighbors = []
        for d in directions:
            n=(node[0]+d[0], node[1]+d[1])
            if 0<=n[0]<GRID_SIZE and 0<=n[1]<GRID_SIZE and n not in avoid_positions and grid[n[1]][n[0]] != -1:
                cost = grid[n[1]][n[0]] if grid[n[1]][n[0]]>1 else 1
                neighbors.append((n,cost))
        return neighbors

    def move(self, shared_state):
        if not self.active:
            return
        if self.position == self.target:
            shared_state.update_cell(self.position, None)
            self.active = False
            self.collided = False
            print(f"{self.role.capitalize()} Car at {self.position} (Prio {self.priority}) reached target.")
            return
        if self.path:
            next_position = self.path[0]
            if not shared_state.is_cell_free(next_position):
                occupant = shared_state.get_car_at_position(next_position)
                if occupant and occupant.priority > self.priority:
                    shared_state.send_message(self, occupant, "yield_request")
                # After communication, try again
                if shared_state.is_cell_free(next_position):
                    self.execute_move(shared_state, next_position)
                else:
                    # Broadcast path to encourage others to avoid
                    shared_state.broadcast_path(self, self.path)
                    self.recalculate_path(shared_state)
            else:
                self.execute_move(shared_state, next_position)
        else:
            self.recalculate_path(shared_state)

    def execute_move(self, shared_state, next_position):
        if shared_state.is_cell_free(next_position):
            shared_state.update_cell(self.position, next_position)
            self.position = next_position
            self.visited_positions.append(self.position)
            self.path.pop(0)
            self.collided = False
            self.receive_reward(0.1)
        else:
            # broadcast path to help others avoid blocked path
            shared_state.broadcast_path(self, self.path)
            self.recalculate_path(shared_state)

    def recalculate_path(self, shared_state):
        self.collided = True
        avoid_positions = shared_state.get_occupied_positions()
        new_path = self.find_path(shared_state.grid, avoid_positions)
        if not new_path:
            print(f"{self.role.capitalize()} Car at {self.position} (Prio {self.priority}) stuck!")
            self.receive_reward(-2)
        else:
            self.path = new_path

    def receive_reward(self, reward):
        # Q-values updated in find_path step, 
        # but we could integrate more updates here if we had full transitions tracked.
        pass

    def draw(self, screen):
        if not self.active:
            return
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
        color = COLLISION_COLOR if self.collided else self.color
        # Leaders get a border for distinction
        if self.role == "leader":
            border_color = (255, 215, 0)  # gold border
            pygame.draw.rect(
                screen,
                border_color,
                (
                    self.position[0]*CELL_SIZE,
                    self.position[1]*CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE,
                ),
            )
            inner_rect = (
                self.position[0]*CELL_SIZE+2,
                self.position[1]*CELL_SIZE+2,
                CELL_SIZE-4,
                CELL_SIZE-4
            )
            pygame.draw.rect(screen, color, inner_rect)
        else:
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
