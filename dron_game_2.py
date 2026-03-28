class Drone:
    def __init__(self):
        self.position = (0, 0)  # Fixed position at the center

    def update(self):
        # No movement, static at center
        pass

class Target:
    def __init__(self):
        self.relative_position = (0, 0)  # Relative to center

    def update_position(self, target_x, target_y):
        # Update position based on input relative to drone at center
        self.relative_position = (target_x, target_y)

    def get_absolute_position(self):
        # Translate to absolute position based on the drone's position
        return (self.relative_position[0], self.relative_position[1])