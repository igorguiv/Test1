CAMERA_SPEED_MULTIPLIER = 1.5

# existing lines and code underneath

class Drone:
    def __init__(self):
        # existing initialization...
        self.camera_offset_x = 0
        self.camera_offset_y = 0

    def update_manual(self):
        # update logic to control camera instead of crosshair using CAMERA_SPEED_MULTIPLIER...  

    def center(self):
        return (WIDTH // 2, HEIGHT // 2)

class Target:
    def draw(self, camera_offset):
        # drawing logic here...

# Update target.update and target.draw calls:
# target.update(WIDTH//2, HEIGHT//2)
# target.draw(camera_offset)
