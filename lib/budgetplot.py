#!/usr/bin/env python3
"""
Collection of plot utilities for the terminal!
Including:
  > piechart
"""

import math

class BudgetPlotter:
    def __init__(self):
        self.color_RED = '\033[91m'
        self.color_GREEN = '\033[92m'
        self.color_YELLOW = '\033[93m'
        self.color_BLUE = '\033[94m'
        self.color_MAGENTA = '\033[95m'
        self.color_CYAN = '\033[96m'
        self.color_ORANGE = '\033[38;5;208m'
        self.color_PURPLE = '\033[38;5;135m'
        self.color_PINK = '\033[38;5;213m'
        self.color_LIME = '\033[38;5;118m'
        self.color_RESET = '\033[0m'
        self.color_BOLD = '\033[1m'

    def draw_pie_chart(self, data, width=40, height=20):
        """
        Draw a pie chart in the terminal using colored blocks

        Args:
            data: Dictionary with labels as keys and values as values
            width: Width of the chart in characters
            height: Height of the chart in characters
        """
        # Calculate total and percentages
        total = sum(data.values())
        percentages = {k: (v / total) * 100 for k, v in data.items()}

        # Calculate angles for each segment (in radians)
        angles = []
        cumulative = 0
        for value in data.values():
            angle = (value / total) * 2 * math.pi
            angles.append((cumulative, cumulative + angle))
            cumulative += angle

        # Colors for different segments
        colors = [
            self.color_RED,
            self.color_GREEN,
            self.color_BLUE,
            self.color_YELLOW,
            self.color_MAGENTA,
            self.color_CYAN,
            self.color_ORANGE,
            self.color_PURPLE,
            self.color_PINK,
            self.color_LIME
        ]

        # Use dots for better visibility
        dot = '█'
        # ░ ▒ ▓ █

        # Center of the circle
        cx, cy = width // 2, height // 2
        radius = min(cx, cy) - 1

        # Create the grid
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        color_grid = [['' for _ in range(width)] for _ in range(height)]

        # Draw the pie chart
        for y in range(height):
            for x in range(width):
                # Calculate distance from center
                dx = x - cx
                dy = (y - cy) * 2  # Multiply by 2 to account for character aspect ratio
                distance = math.sqrt(dx**2 + dy**2)

                if distance <= radius:
                    # Calculate angle
                    angle = math.atan2(dy, dx)
                    if angle < 0:
                        angle += 2 * math.pi

                    # Determine which segment this point belongs to
                    for i, (start, end) in enumerate(angles):
                        if start <= angle < end:
                            grid[y][x] = f'{dot}'
                            color_grid[y][x] = colors[i % len(colors)]
                            break

        # Prepare legend items
        items = list(data.items())
        legend_lines = []
        for i, (label, value) in enumerate(items):
            color = colors[i % len(colors)]
            percentage = percentages[label]
            legend_lines.append(f"{color}{dot}{dot}{self.color_RESET} {label}: {value} ({percentage:.1f}%)")
        legend_lines.append(f"{self.color_BOLD}Total: {total}{self.color_RESET}")

        # Calculate legend width (find max length, accounting for ANSI codes)
        import re
        max_legend_len = 0
        for line in legend_lines:
            # Remove ANSI codes to get actual visible length
            visible = re.sub(r'\033\[[0-9;]+m', '', line)
            max_legend_len = max(max_legend_len, len(visible))

        # Find the actual bounds of the pie chart (trim empty rows)
        first_row = 0
        last_row = height - 1
        for y in range(height):
            if any(grid[y][x] == f'{dot}' for x in range(width)):
                first_row = y
                break
        for y in range(height - 1, -1, -1):
            if any(grid[y][x] == f'{dot}' for x in range(width)):
                last_row = y
                break

        chart_height = last_row - first_row + 1

        # Center legend vertically with the pie chart
        legend_start = (chart_height - len(legend_lines)) // 2
        if legend_start < 0:
            legend_start = 0

        # Print only the rows that contain the pie chart
        print()
        for y in range(first_row, last_row + 1):
            line = ''
            for x, char in enumerate(grid[y]):
                if char == f'{dot}':
                    line += color_grid[y][x] + f'{dot}' + self.color_RESET
                else:
                    line += ' '

            # Add legend on the right side, centered
            legend_index = y - first_row - legend_start
            if 0 <= legend_index < len(legend_lines):
                # Calculate visible length for proper padding
                visible = re.sub(r'\033\[[0-9;]+m', '', line)
                padding = width - len(visible)
                line += ' ' * padding + ' │ ' + legend_lines[legend_index]
            else:
                # Just add spacing for alignment
                visible = re.sub(r'\033\[[0-9;]+m', '', line)
                padding = width - len(visible)
                line += ' ' * padding

            print(line)

        print()


if __name__ == "__main__":
    # Dummy data - Sales by product category
    dummy_data = {
        "Electronics": 450,
        "Clothing": 320,
        "Food": 180,
        "Books": 150,
        "Toys": 100
    }

    plotter = BudgetPlotter()
    plotter.draw_pie_chart(dummy_data, width=40, height=22)


    #draw_pie_chart(dummy_data, width=40, height=22)
