from config import GRID_SIZE, TARGET_ZONE_SIZE
import random

class SharedState:
    def __init__(self):
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.predicted_positions = set()
        self.cars = []  # Keep track of cars for communication and position queries
        self.messages = []  # Simple message queue

        self.place_obstacles()

    def register_car(self, car):
        """Register a car in the shared state."""
        self.cars.append(car)

    def place_obstacles(self):
        """Places static obstacles randomly, avoiding the target zone."""
        num_obstacles = int(GRID_SIZE * GRID_SIZE * 0.1)  # 10% obstacles
        for _ in range(num_obstacles):
            while True:
                x = random.randint(0, GRID_SIZE - 1)
                y = random.randint(0, GRID_SIZE - 1)
                if self.grid[y][x] == 0 and not self.is_in_target_zone((x, y)):
                    self.grid[y][x] = -1
                    break

    def move_random_obstacle(self):
        """Move an obstacle randomly to simulate a dynamic environment."""
        # Find an existing obstacle and try to move it somewhere else free.
        obstacle_positions = [(x, y) for y in range(GRID_SIZE) for x in range(GRID_SIZE) if self.grid[y][x] == -1]
        if obstacle_positions:
            old_pos = random.choice(obstacle_positions)
            new_pos = (random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1))
            if self.grid[new_pos[1]][new_pos[0]] == 0 and not self.is_in_target_zone(new_pos):
                # Move obstacle
                self.grid[old_pos[1]][old_pos[0]] = 0
                self.grid[new_pos[1]][new_pos[0]] = -1

    def is_in_target_zone(self, position):
        center = GRID_SIZE // 2
        target_range = range(center - TARGET_ZONE_SIZE // 2, center + TARGET_ZONE_SIZE // 2 + 1)
        return position[0] in target_range and position[1] in target_range

    def is_cell_free(self, position):
        x, y = position
        if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
            return False
        return (
            self.grid[y][x] == 0
            and position not in self.predicted_positions
            and self.grid[y][x] != -1
        )

    def update_cell(self, old_position, new_position):
        if old_position:
            old_x, old_y = old_position
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
        """Returns the car occupying a given position, if any."""
        for car in self.cars:
            if car.active and car.position == position:
                return car
        return None

    def send_message(self, sender, receiver, content):
        """Send a message from one car to another."""
        self.messages.append((sender, receiver, content))

    def process_messages(self):
        """Process pending messages. For now, handle simple yield requests."""
        new_messages = []
        for msg in self.messages:
            sender, receiver, content = msg
            if content == "yield_request":
                # If receiver has lower priority (higher number), try to move aside or wait
                if receiver.priority > sender.priority:
                    # Attempt a small "reroute" by removing receiver's next path cell, forcing recalculation
                    if receiver.path:
                        # Remove one step from receiver path to force recalculation
                        receiver.path.pop(0)
                        receiver.collided = True  # Force them to recalc next move
                    else:
                        # If no path, receiver just waits and tries next frame.
                        pass
                # If receiver has equal or higher priority, ignore request.
            else:
                # Other message types could be added.
                pass
        self.messages = new_messages  # Clear processed messages

