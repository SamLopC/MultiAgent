from config import GRID_SIZE, TARGET_ZONE_SIZE
import random

class SharedState:
    def __init__(self):
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.predicted_positions = set()
        self.cars = []
        self.messages = []
        self.place_obstacles()

    def register_car(self, car):
        self.cars.append(car)

    def place_obstacles(self):
        num_obstacles = int(GRID_SIZE * GRID_SIZE * 0.1)
        for _ in range(num_obstacles):
            while True:
                x = random.randint(0, GRID_SIZE - 1)
                y = random.randint(0, GRID_SIZE - 1)
                if self.grid[y][x] == 0 and not self.is_in_target_zone((x, y)):
                    self.grid[y][x] = -1
                    break

    def move_random_obstacle(self):
        # Moves an existing obstacle to a free cell
        obstacle_positions = [(x,y) for y in range(GRID_SIZE) for x in range(GRID_SIZE) if self.grid[y][x] == -1]
        if obstacle_positions:
            old_pos = random.choice(obstacle_positions)
            new_pos = (random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1))
            if self.grid[new_pos[1]][new_pos[0]] == 0 and not self.is_in_target_zone(new_pos):
                self.grid[old_pos[1]][old_pos[0]] = 0
                self.grid[new_pos[1]][new_pos[0]] = -1

    def remove_random_obstacle(self):
        # Remove an obstacle entirely
        obstacle_positions = [(x,y) for y in range(GRID_SIZE) for x in range(GRID_SIZE) if self.grid[y][x] == -1]
        if obstacle_positions:
            pos = random.choice(obstacle_positions)
            self.grid[pos[1]][pos[0]] = 0

    def increase_random_cell_cost(self):
        free_positions = [(x,y) for y in range(GRID_SIZE) for x in range(GRID_SIZE)
                          if self.grid[y][x]>=0 and not self.is_in_target_zone((x,y))]
        if free_positions:
            pos = random.choice(free_positions)
            self.grid[pos[1]][pos[0]] = max(1, self.grid[pos[1]][pos[0]]+1)

    def is_in_target_zone(self, position):
        center = GRID_SIZE // 2
        target_range = range(center - TARGET_ZONE_SIZE // 2, center + TARGET_ZONE_SIZE // 2 + 1)
        return position[0] in target_range and position[1] in target_range

    def is_cell_free(self, position):
        x, y = position
        if not (0<=x<GRID_SIZE and 0<=y<GRID_SIZE):
            return False
        return (
            self.grid[y][x]>=0
            and position not in self.predicted_positions
            and self.grid[y][x]!=1
        )

    def update_cell(self, old_position, new_position):
        if old_position:
            old_x, old_y = old_position
            if self.grid[old_y][old_x] == 1:
                self.grid[old_y][old_x] = 0
        if new_position:
            new_x, new_y = new_position
            self.grid[new_y][new_x] = 1

    def predict_position(self, position):
        self.predicted_positions.add(position)

    def clear_predictions(self):
        self.predicted_positions.clear()

    def get_occupied_positions(self):
        occupied_positions = set()
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid[y][x] == 1:
                    occupied_positions.add((x, y))
        return occupied_positions

    def get_car_at_position(self, position):
        for c in self.cars:
            if c.active and c.position == position:
                return c
        return None

    def get_leader(self):
        leaders = [c for c in self.cars if c.role == "leader" and c.active]
        return leaders[0] if leaders else None

    def send_message(self, sender, receiver, content):
        self.messages.append((sender, receiver, content))

    def broadcast_path(self, sender, path):
        # Broadcast intended path so lower priority cars might reroute
        for c in self.cars:
            if c.active and c != sender and c.priority > sender.priority:
                self.messages.append((sender, c, ("path_broadcast", path)))

    def process_messages(self):
        yield_requests = 0
        yields_honored = 0
        new_messages = []
        for msg in self.messages:
            sender, receiver, content = msg
            if content == "yield_request":
                yield_requests += 1
                # If receiver has lower priority than sender
                if receiver.priority > sender.priority:
                    if receiver.path:
                        receiver.path.pop(0)
                        receiver.collided = True
                        yields_honored += 1
            elif isinstance(content, tuple) and content[0] == "path_broadcast":
                _, path = content
                # If receiver is lower priority and active, try to avoid path intersection
                if receiver.priority > sender.priority and receiver.active and receiver.path:
                    intersect = set(receiver.path).intersection(set(path))
                    if len(intersect) > 2:
                        receiver.collided = True
            # No else case needed if no other message types

        # After processing all messages, clear them
        self.messages = new_messages
        return {"requests": yield_requests, "honored": yields_honored}

