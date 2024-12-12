import pygame
import random
import logging
import time
from collections import defaultdict, deque
from grid import draw_grid, draw_target_zone
from car import Car  # Ensure this is implemented correctly
from shared_state import SharedState  # Ensure shared_state is implemented correctly
from config import GRID_SIZE, CELL_SIZE, FPS, TARGET_ZONE_SIZE, WHITE, CAR_COLORS


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs.log'
)

def main(num_cars=10):
    # User-configurable parameters
    # num_cars: How many cars to spawn (to test scalability)

    # Toggle centralized vs. decentralized control
    centralized_control = True  # Let's default to decentralized for variety

    pygame.init()
    screen = pygame.display.set_mode((GRID_SIZE * CELL_SIZE, GRID_SIZE * CELL_SIZE))
    pygame.display.set_caption("Multi-Agent Pathfinding")
    clock = pygame.time.Clock()
    shared_state = SharedState()

    logging.info("Starting Multi-Agent Pathfinding Simulation")

    cars = []
    occupied_positions = set()
    target_positions = set()

    # Define central target zone
    center = GRID_SIZE // 2
    target_range = range(center - TARGET_ZONE_SIZE // 2, center + TARGET_ZONE_SIZE // 2 + 1)
    for x in target_range:
        for y in target_range:
            target_positions.add((x, y))

    # Assign roles and priorities with a slightly larger scenario
    # Leaders: first 3 cars
    # Followers: next num_cars//3 cars (approx.)
    # Normal: rest
    num_leaders = min(3, num_cars)
    num_followers = max(0, num_cars // 3)
    num_normal = num_cars - num_leaders - num_followers

    roles = ["leader"] * num_leaders + ["follower"] * num_followers + ["normal"] * num_normal
    priorities = [1]*num_leaders + [2]*num_followers + [3]*num_normal

    # Group target for followers
    group_target_cells = list(target_positions)
    group_target = random.choice(group_target_cells) if group_target_cells else None
    if group_target and group_target in target_positions:
        target_positions.remove(group_target)

    # Metrics
    total_collisions = 0
    cars_finished = 0
    finish_times = []
    start_time = time.time()
    path_algo_switch_count = 0
    yield_requests = 0
    yields_honored = 0
    synergy_bonus = 0

    # Car initialization
    for i in range(num_cars):
        placement_attempts = 0
        while placement_attempts < 200:
            # Spread cars more towards the edges if possible
            # This makes the scenario more challenging
            edge_preference = random.choice(["top", "bottom", "left", "right"])
            if edge_preference == "top":
                start = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE//4))
            elif edge_preference == "bottom":
                start = (random.randint(0, GRID_SIZE - 1), random.randint(GRID_SIZE - GRID_SIZE//4, GRID_SIZE - 1))
            elif edge_preference == "left":
                start = (random.randint(0, GRID_SIZE//4), random.randint(0, GRID_SIZE - 1))
            else:
                start = (random.randint(GRID_SIZE - GRID_SIZE//4, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

            if start not in occupied_positions and start not in target_positions and start != group_target:
                occupied_positions.add(start)
                break
            placement_attempts += 1
        
        if placement_attempts >= 200:
            logging.error(f"Failed to place car {i}")
            continue

        role = roles[i % len(roles)]
        priority = priorities[i % len(priorities)]

        # Determine target
        if role == "leader":
            possible_targets = list(target_positions)
            if not possible_targets:
                # fallback if no unique targets left
                possible_targets = [group_target] if group_target else list(target_positions)
            target = random.choice(possible_targets) if possible_targets else group_target
            if target in target_positions:
                target_positions.remove(target)
        elif role == "follower":
            target = group_target if group_target else random.choice(list(target_positions)) if target_positions else None
        else:
            # normal
            possible_targets = list(target_positions)
            if possible_targets:
                target = random.choice(possible_targets)
                target_positions.remove(target)
            else:
                target = group_target

        if not target:
            logging.error(f"No target found for car {i}")
            continue

        color = CAR_COLORS[i % len(CAR_COLORS)]
        car = Car(start, target, color=color, priority=priority, role=role)
        avoid_positions = shared_state.get_occupied_positions()
        car.path = car.find_path(shared_state.grid, avoid_positions)
        if not car.path:
            logging.error(f"Car {i} failed to calculate a path from {start} to {target}")
        else:
            cars.append(car)
            shared_state.register_car(car)
            shared_state.update_cell(None, start)
            logging.info(f"Car {i} (Role: {role}, Priority: {priority}) initialized: Start {start}, Target {target}")

    SIMULATION_TIMEOUT = 300  # More time for a bigger scenario
    move_timer = 0
    move_delay = 400  # Faster moves
    running = True

    # Centralized controller (if enabled)
    def centralized_controller(cars, shared_state):
        for car in cars:
            if car.active:
                avoid_positions = shared_state.get_occupied_positions()
                new_path = car.find_path(shared_state.grid, avoid_positions)
                if new_path and (not car.path or len(new_path) < len(car.path)):
                    car.path = new_path

    last_log_time = time.time()

    while running:
        if time.time() - start_time > SIMULATION_TIMEOUT:
            logging.warning("Simulation timed out")
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        shared_state.clear_predictions()
        yield_info = shared_state.process_messages()
        yield_requests += yield_info["requests"]
        yields_honored += yield_info["honored"]

        # Dynamic environment: add/remove obstacles randomly
        if random.random() < 0.005:
            shared_state.move_random_obstacle()
        if random.random() < 0.005:
            shared_state.increase_random_cell_cost()
        if random.random() < 0.002:
            shared_state.remove_random_obstacle()

        current_time = pygame.time.get_ticks()
        if current_time - move_timer > move_delay:
            move_timer = current_time

            if centralized_control and random.random() < 0.03:
                centralized_controller(cars, shared_state)

            for car in cars:
                if car.active:
                    old_path_len = len(car.path)
                    car.move(shared_state)
                    # If length changed drastically, might have switched algos internally
                    if len(car.path) != old_path_len:
                        path_algo_switch_count += 1
                    if car.collided:
                        total_collisions += 1
                        car.receive_reward(-5)
                    if not car.active and car.position == car.target:
                        finish_times.append(time.time() - start_time)
                        cars_finished += 1
                        car.receive_reward(10)  # success
                        # Check synergy: If this is a follower and recently a leader finished, reward synergy
                        if car.role == "follower":
                            leader = shared_state.get_leader()
                            if leader and not leader.active:  
                                # If leader finished close in time, synergy bonus
                                time_diff = abs((time.time() - start_time) - finish_times[-1])  # last finish
                                if time_diff < 10:
                                    synergy_bonus += 5
                                    car.receive_reward(5)

                    # Followers try to stay close to leader
                    if car.role == "follower":
                        leader = shared_state.get_leader()
                        if leader and leader.active:
                            dist = abs(car.position[0]-leader.position[0]) + abs(car.position[1]-leader.position[1])
                            if dist > 12:
                                avoid_positions = shared_state.get_occupied_positions()
                                old_target = car.target
                                car.target = leader.position
                                new_path = car.find_path(shared_state.grid, avoid_positions)
                                if new_path:
                                    car.path = new_path
                                car.target = old_target

        # Periodic progress logging
        if time.time() - last_log_time > 10:
            logging.info(f"Progress update: {cars_finished}/{len(cars)} cars finished, collisions so far: {total_collisions}")
            last_log_time = time.time()

        # Rendering
        screen.fill(WHITE)
        draw_grid(screen, shared_state)
        draw_target_zone(screen)

        for car in cars:
            car.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

        if all(not car.active for car in cars if car.target):
            logging.info("All cars reached their targets")
            break

    pygame.quit()
    logging.info("Simulation ended")

    if finish_times:
        avg_time = sum(finish_times) / len(finish_times)
    else:
        avg_time = 0

    logging.info(f"Total collisions: {total_collisions}")
    logging.info(f"Cars finished: {cars_finished}/{len(cars)}")
    logging.info(f"Average finish time: {avg_time:.2f} s")
    logging.info(f"Path algo switch count: {path_algo_switch_count}")
    logging.info(f"Yield requests: {yield_requests}, Yields honored: {yields_honored}")
    logging.info(f"Synergy bonus total: {synergy_bonus}")

    print("Simulation completed.")
    print(f"Total collisions: {total_collisions}")
    print(f"Cars finished: {cars_finished}/{len(cars)}")
    print(f"Average finish time: {avg_time:.2f} s")
    print(f"Path algo switch count: {path_algo_switch_count}")
    print(f"Yield requests: {yield_requests}, Yields honored: {yields_honored}")
    print(f"Synergy bonus total: {synergy_bonus}")

if __name__ == "__main__":
    # Test with more than 10 cars
    main(num_cars=10)
