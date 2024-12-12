# grid.py

import pygame
from config import GRID_SIZE, CELL_SIZE, WHITE, TARGET_ZONE_COLOR, OBSTACLE_COLOR, GRID_COLOR, TARGET_ZONE_SIZE

def draw_grid(screen, shared_state):
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if shared_state.grid[y][x] == -1:
                pygame.draw.rect(screen, OBSTACLE_COLOR, rect)
            else:
                # Draw grid lines
                pygame.draw.rect(screen, GRID_COLOR, rect, 1)

def draw_target_zone(screen):
    """Draws the target zone in the center of the grid."""
    start_x = (GRID_SIZE // 2 - TARGET_ZONE_SIZE // 2)
    start_y = (GRID_SIZE // 2 - TARGET_ZONE_SIZE // 2)
    for y in range(TARGET_ZONE_SIZE):
        for x in range(TARGET_ZONE_SIZE):
            rect = pygame.Rect(
                (start_x + x) * CELL_SIZE,
                (start_y + y) * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(screen, TARGET_ZONE_COLOR, rect)
