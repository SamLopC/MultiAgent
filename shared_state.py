from config import GRID_SIZE, TARGET_ZONE_SIZE
import random

class SharedState:
    def __init__(self):
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.predicted_positions = set()
        self.place_obstacles()

    def place_obstacles(self):
        """Randomly places obstacles on the grid, avoiding the target zone and starting positions."""
        num_obstacles = int(GRID_SIZE * GRID_SIZE * 0.1)  # 10% of the grid
        for _ in range(num_obstacles):
            while True:
                x = random.randint(0, GRID_SIZE - 1)
                y = random.randint(0, GRID_SIZE - 1)
                if self.grid[y][x] == 0 and not self.is_in_target_zone((x, y)):
                    self.grid[y][x] = -1  # Mark as obstacle
                    break

    def is_in_target_zone(self, position):
        """Checks if a position is within the target zone."""
        center = GRID_SIZE // 2
        target_range = range(center - TARGET_ZONE_SIZE // 2, center + TARGET_ZONE_SIZE // 2 + 1)
        return position[0] in target_range and position[1] in target_range

    def is_cell_free(self, position):
        """Checks if a cell is free for movement."""
        x, y = position
        return (
            0 <= x < GRID_SIZE
            and 0 <= y < GRID_SIZE
            and self.grid[y][x] == 0  # Cell is not currently occupied
            and position not in self.predicted_positions  # Cell is not predicted to be occupied
            and self.grid[y][x] != -1  # Cell is not an obstacle
        )
        
    def update_cell(self, old_position, new_position):
        """Updates the grid with the car's movement."""
        if old_position:
            old_x, old_y = old_position
            self.grid[old_y][old_x] = 0
        if new_position:
            new_x, new_y = new_position
            self.grid[new_y][new_x] = 1

    def predict_position(self, position):
        """Marks a position as predicted to be occupied soon."""
        self.predicted_positions.add(position)

    def clear_predictions(self):
        """Clears all predicted positions."""
        self.predicted_positions.clear()

    def get_occupied_positions(self):
        """Returns a set of all occupied positions."""
        occupied_positions = set()
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid[y][x] == 1:
                    occupied_positions.add((x, y))
        return occupied_positions