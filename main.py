import pygame
import random
import logging
import time
from collections import defaultdict
from grid import draw_grid, draw_target_zone
from car import Car  # Ensure this is implemented correctly
from shared_state import SharedState  # Ensure shared_state is implemented correctly
from config import GRID_SIZE, CELL_SIZE, FPS, TARGET_ZONE_SIZE, WHITE, CAR_COLORS

# -----------------------------------------------------------------------------
# Enhanced Multi-Agent Pathfinding
# Features added:
# - Advanced collision avoidance heuristics
# - Simple agent communication via a shared messaging system
# - Placeholder for reinforcement learning signals (reward structure)
# - Prioritization of certain agents
# - Performance evaluations and logging metrics
# - Potential for dynamic environment (e.g., moving obstacles)
# - More complex environmental factors (optional demonstration)

# Note: This code adds a framework for the additional features. A full RL 
# implementation or sophisticated multi-agent communication is non-trivial 
# and would require further development. However, this code demonstrates 
# how to integrate and structure these concepts within the existing framework.
# -----------------------------------------------------------------------------

# Configure logging for the entire simulation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs.log'
)

def main():
    # Initialize Pygame and setup
    pygame.init()
    screen = pygame.display.set_mode((GRID_SIZE * CELL_SIZE, GRID_SIZE * CELL_SIZE))
    pygame.display.set_caption("Advanced Multi-Agent Pathfinding")
    clock = pygame.time.Clock()
    shared_state = SharedState()

    # Logging start of simulation
    logging.info("Starting Advanced Multi-Agent Pathfinding Simulation")

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

    # Assign different priorities (e.g., some cars are "emergency" with higher priority)
    # Priority 1 is highest, larger number is lower priority.
    # Just as an example, let's make the first 3 cars higher priority.
    car_priorities = [1 if i < 3 else 2 for i in range(10)]

    # Metrics
    total_collisions = 0
    cars_finished = 0
    finish_times = []
    start_time = time.time()

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
        car = Car(start, target, color=color, priority=car_priorities[i])
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
            shared_state.register_car(car)  # Let shared_state know about this car
            shared_state.update_cell(None, start)  # Mark starting position as occupied
            logging.info(f"Car {i} initialized: Start {start}, Target {target}, Priority {car.priority}")
        else:
            logging.error(f"Car {i} failed to calculate a path from {start} to {target}")

    # Simulation settings
    SIMULATION_TIMEOUT = 120  # extended seconds for more complex scenario
    move_timer = 0
    move_delay = 300  # Milliseconds between moves (faster simulation)
    running = True

    # Main simulation loop
    while running:
        # Check for simulation timeout
        if time.time() - start_time > SIMULATION_TIMEOUT:
            logging.warning("Simulation timed out")
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Clear predictions for this frame and messages
        shared_state.clear_predictions()
        shared_state.process_messages()

        # Potential dynamic environment update (e.g., move some obstacles)
        # Here, we can periodically move obstacles or introduce dynamic elements.
        if random.random() < 0.01:
            shared_state.move_random_obstacle()

        # Move cars and update their positions
        current_time = pygame.time.get_ticks()
        if current_time - move_timer > move_delay:
            move_timer = current_time  # Reset the move timer

            for car in cars:
                if car.active:
                    # The move method includes fallback pathfinding and communication
                    car.move(shared_state)
                    # Record if collision happened
                    if car.collided:
                        total_collisions += 1
                        # RL reward signal (negative reward for collision)
                        car.receive_reward(-5)

                    # If reached target, record metrics
                    if not car.active and car.position == car.target:
                        finish_times.append(time.time() - start_time)
                        cars_finished += 1
                        # RL reward signal (positive reward for success)
                        car.receive_reward(10)

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
        if all(not car.active for car in cars):
            logging.info("All cars reached their targets")
            break

    # End of simulation
    pygame.quit()
    logging.info("Simulation ended")

    # Log performance metrics
    if finish_times:
        avg_time = sum(finish_times) / len(finish_times)
    else:
        avg_time = 0
    logging.info(f"Total collisions: {total_collisions}")
    logging.info(f"Cars finished: {cars_finished}/{len(cars)}")
    logging.info(f"Average finish time: {avg_time:.2f} s")

    print("Simulation completed.")
    print(f"Total collisions: {total_collisions}")
    print(f"Cars finished: {cars_finished}/{len(cars)}")
    print(f"Average finish time: {avg_time:.2f} s")

if __name__ == "__main__":
    main()
