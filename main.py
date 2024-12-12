import pygame
import random
import logging
import time
from grid import draw_grid, draw_target_zone
from car import Car  # Ensure this is implemented correctly
from shared_state import SharedState  # Ensure shared_state is implemented correctly
from config import GRID_SIZE, CELL_SIZE, FPS, TARGET_ZONE_SIZE, WHITE, CAR_COLORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs.log'
)

def main():
    # Initialize Pygame and setup
    pygame.init()
    screen = pygame.display.set_mode((GRID_SIZE * CELL_SIZE, GRID_SIZE * CELL_SIZE))
    pygame.display.set_caption("Multi-Agent Pathfinding")
    clock = pygame.time.Clock()
    shared_state = SharedState()

    # Logging start of simulation
    logging.info("Starting Multi-Agent Pathfinding Simulation")

    # Initialize cars
    cars = []
    occupied_positions = set()
    target_positions = set()

    # Define central target zone coordinates
    center = GRID_SIZE // 2
    target_range = range(center - TARGET_ZONE_SIZE // 2, center + TARGET_ZONE_SIZE // 2 + 1)
    for x in target_range:
        for y in target_range:
            target_positions.add((x, y))

    # Car initialization
    for i in range(10):  # Example with 10 cars
        placement_attempts = 0
        while placement_attempts < 100:
            start = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
            if start not in occupied_positions and start not in target_positions:
                occupied_positions.add(start)
                break
            placement_attempts += 1
        
        if placement_attempts >= 100:
            logging.error(f"Failed to place car {i}")
            continue

        available_targets = list(target_positions - occupied_positions)
        if not available_targets:
            logging.error(f"No available target positions for car {i}")
            continue
        
        target = random.choice(available_targets)
        occupied_positions.add(target)

        color = CAR_COLORS[i % len(CAR_COLORS)]
        car = Car(start, target, color=color)
        avoid_positions = shared_state.get_occupied_positions()

        # Try A* first
        car.path = car.a_star(shared_state.grid, avoid_positions)
        # If A* fails, try BFS
        if not car.path:
            car.path = car.breadth_first_search(shared_state.grid, avoid_positions)
        # If BFS fails, try Dijkstra
        if not car.path:
            car.path = car.dijkstra(shared_state.grid, avoid_positions)

        if car.path:
            cars.append(car)
            shared_state.update_cell(None, start)  # Mark starting position as occupied
            logging.info(f"Car {i} initialized: Start {start}, Target {target}")
        else:
            logging.error(f"Car {i} failed to calculate a path from {start} to {target}")

    # Simulation timeout
    SIMULATION_TIMEOUT = 60  # seconds
    start_time = time.time()

    move_timer = 0
    move_delay = 500  # Milliseconds between moves

    running = True
    while running:
        # Check for simulation timeout
        if time.time() - start_time > SIMULATION_TIMEOUT:
            logging.warning("Simulation timed out")
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Clear predictions for this frame
        shared_state.clear_predictions()

        # Move cars and update their positions
        current_time = pygame.time.get_ticks()
        if current_time - move_timer > move_delay:
            move_timer = current_time  # Reset the move timer

            for car in cars:
                if car.active:  # Only move active cars
                    # When moving, if the path is blocked, the Car class will attempt
                    # A*, then BFS, then Dijkstra in its move method fallback logic.
                    car.move(shared_state)

        # Clear the screen
        screen.fill(WHITE)

        # Draw the grid and target zone
        draw_grid(screen, shared_state)
        draw_target_zone(screen)

        # Draw the cars
        for car in cars:
            car.draw(screen)

        # Update the display
        pygame.display.flip()
        clock.tick(FPS)

        # End simulation if all cars have reached their targets
        if not any(car.active for car in cars):
            logging.info("All cars reached their targets")
            break

    # End of simulation
    pygame.quit()
    logging.info("Simulation ended")

if __name__ == "__main__":
    main()
