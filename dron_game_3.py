import pygame
import sys
import random
import math

# --- Вікно та «монітор» ---
WIDTH, HEIGHT = 800, 600
FPS = 60

BEZEL_TOP = 18
BEZEL_SIDE = 20
BEZEL_BOTTOM = 44

SCREEN_RECT = pygame.Rect(
    BEZEL_SIDE,
    BEZEL_TOP,
    WIDTH - 2 * BEZEL_SIDE,
    HEIGHT - BEZEL_TOP - BEZEL_BOTTOM,
)
VIEW_W = SCREEN_RECT.width
VIEW_H = SCREEN_RECT.height
VIEW_CX = VIEW_W // 2
VIEW_CY = VIEW_H // 2

# Світ (ціль блукає тут; камера їздить стрілками)
WORLD_W = 2400
WORLD_H = 1600

SKY_COLOR = (135, 206, 235)
BEZEL_COLOR = (42, 44, 52)
STAND_COLOR = (55, 58, 66)
CROSSHAIR_COLOR = (0, 255, 0)
SQUARE_COLOR = (255, 0, 0)
TARGET_COLOR = (0, 0, 0)

CROSSHAIR_RADIUS = 4
SQUARE_SIZE = 120  # сторона червоного квадрата прицілу

TARGET_OUTLINE_WIDTH = 3
TARGET_INITIAL_SIZE = 60  # Початковий розмір цілі (для масштабування)
TARGET_SPEED_KMH = 200
TARGET_SPEED_PX_PER_S = TARGET_SPEED_KMH * 1000 / 3600 * (1/3)  # масштабування до пікселів

DRONE_MIN_SPEED_KMH = 100
DRONE_MAX_SPEED_KMH = 300
DRONE_SPEED_STEP = 10

FONT_SIZE = 30

# Хаотична ціль: як часто міняти напрям (сек)
TARGET_TURN_MIN = 0.15
TARGET_TURN_MAX = 0.65


def world_to_screen(wx, wy, cam_x, cam_y):
    return wx - cam_x + VIEW_CX, wy - cam_y + VIEW_CY


def clamp_camera(cam_x, cam_y):
    half_w = VIEW_W / 2
    half_h = VIEW_H / 2
    cx = max(half_w, min(WORLD_W - half_w, cam_x))
    cy = max(half_h, min(WORLD_H - half_h, cam_y))
    return cx, cy


def draw_shahed(surface, center, size):
    x, y = center
    w = size * 1.5
    h = size
    pygame.draw.polygon(
        surface,
        TARGET_COLOR,
        [
            (x - 0.2 * w, y + 0.4 * h),
            (x + 0.2 * w, y + 0.4 * h),
            (x + 0.3 * w, y),
            (x, y - 0.4 * h),
            (x - 0.3 * w, y),
        ],
        TARGET_OUTLINE_WIDTH,
    )
    pygame.draw.line(
        surface,
        TARGET_COLOR,
        (x - 0.6 * w, y + 0.15 * h),
        (x + 0.6 * w, y + 0.15 * h),
        TARGET_OUTLINE_WIDTH,
    )
    pygame.draw.line(
        surface,
        TARGET_COLOR,
        (x, y + 0.4 * h),
        (x, y + 0.6 * h),
        TARGET_OUTLINE_WIDTH,
    )
    pygame.draw.line(
        surface,
        TARGET_COLOR,
        (x, y - 0.37 * h),
        (x, y - 0.46 * h),
        TARGET_OUTLINE_WIDTH,
    )


class Target:
    """Ціль у світових координатах; хаотично змінює напрям, не «тікає» від прицілу."""

    def __init__(self, world_cx, world_cy):
        self.x = world_cx + random.randint(-120, 120)
        self.y = world_cy + random.randint(-120, 120)
        self.dir_angle = random.uniform(0, 2 * math.pi)
        self.wander = random.uniform(0, 2 * math.pi)
        self.size = TARGET_INITIAL_SIZE
        self.base_size = TARGET_INITIAL_SIZE
        self.dist_px = 230.0
        self.speed_px = TARGET_SPEED_PX_PER_S
        self._next_turn_in = random.uniform(TARGET_TURN_MIN, TARGET_TURN_MAX)

    def _pick_new_heading(self):
        self.wander += random.uniform(-1.1, 1.1)
        jitter = (random.random() - 0.5) * math.pi * 0.95
        self.dir_angle = self.wander + jitter
        self._next_turn_in = random.uniform(TARGET_TURN_MIN, TARGET_TURN_MAX)

    def update(self, dt, cam_x, cam_y):
        self._next_turn_in -= dt
        if self._next_turn_in <= 0:
            self._pick_new_heading()

        if random.random() < 0.04 * dt * 60:
            self.dir_angle += random.uniform(-0.35, 0.35)

        self.x += self.speed_px * math.cos(self.dir_angle) * dt
        self.y += self.speed_px * math.sin(self.dir_angle) * dt

        margin = 35
        if self.x < margin:
            self.x = margin
            self.dir_angle = random.uniform(-math.pi / 2, math.pi / 2)
        elif self.x > WORLD_W - margin:
            self.x = WORLD_W - margin
            self.dir_angle = math.pi + random.uniform(-math.pi / 2, math.pi / 2)
        if self.y < margin:
            self.y = margin
            self.dir_angle = random.uniform(0, math.pi)
        elif self.y > WORLD_H - margin:
            self.y = WORLD_H - margin
            self.dir_angle = -random.uniform(0, math.pi)

        self.dist_px = math.hypot(self.x - cam_x, self.y - cam_y)
        self.size = int(self.base_size * 200 / max(80.0, self.dist_px))

    def draw(self, surface, cam_x, cam_y):
        sx, sy = world_to_screen(self.x, self.y, cam_x, cam_y)
        draw_shahed(surface, (int(sx), int(sy)), self.size)

    def is_inside_square(self, cam_x, cam_y, square_size):
        hs = square_size // 2
        return abs(self.x - cam_x) <= hs and abs(self.y - cam_y) <= hs

    def covers_half_square(self, square_size):
        return self.size >= square_size // 2

    def covers_whole_view(self):
        return self.size >= max(VIEW_W, VIEW_H) * 1.2


class Camera:
    """Центр огляду в світі; стрілки зсувають картинку, приціл на екрані нерухомий."""

    def __init__(self, wx, wy):
        self.x = wx
        self.y = wy
        self.speed_kmh = DRONE_MIN_SPEED_KMH

    def speed_px_value(self):
        return self.speed_kmh * 1000 / 3600 * (1 / 3)

    def update_manual(self, keys_pressed, dt):
        dx, dy = 0, 0
        if keys_pressed[pygame.K_LEFT]:
            dx -= 1
        if keys_pressed[pygame.K_RIGHT]:
            dx += 1
        if keys_pressed[pygame.K_UP]:
            dy -= 1
        if keys_pressed[pygame.K_DOWN]:
            dy += 1
        n = math.hypot(dx, dy)
        if n != 0:
            dx /= n
            dy /= n
            m = self.speed_px_value() * dt
            self.x += dx * m
            self.y += dy * m
        self.x, self.y = clamp_camera(self.x, self.y)

    def update_auto(self, target: Target, dt):
        dx = target.x - self.x
        dy = target.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 2:
            dx /= dist
            dy /= dist
            self.x += dx * self.speed_px_value() * dt
            self.y += dy * self.speed_px_value() * dt

        if dist > 280:
            self.speed_kmh = DRONE_MAX_SPEED_KMH
        elif dist < 110:
            self.speed_kmh = DRONE_MIN_SPEED_KMH
        else:
            t = (dist - 110) / (280 - 110)
            self.speed_kmh = int(
                DRONE_MIN_SPEED_KMH
                + (DRONE_MAX_SPEED_KMH - DRONE_MIN_SPEED_KMH) * t
            )
        self.x, self.y = clamp_camera(self.x, self.y)


def draw_crosshair_fixed(surface, center):
    x, y = center
    hs = SQUARE_SIZE // 2
    pygame.draw.rect(
        surface, SQUARE_COLOR, (x - hs, y - hs, SQUARE_SIZE, SQUARE_SIZE), 2
    )
    pygame.draw.circle(surface, CROSSHAIR_COLOR, (x, y), CROSSHAIR_RADIUS)


def draw_monitor_frame(screen):
    screen.fill(BEZEL_COLOR)
    pygame.draw.rect(screen, STAND_COLOR, (WIDTH // 2 - 70, HEIGHT - 22, 140, 18))
    pygame.draw.rect(screen, (28, 30, 36), SCREEN_RECT.inflate(4, 4), 3)


def draw_scanlines(view_surface):
    overlay = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    for y in range(0, VIEW_H, 3):
        pygame.draw.line(overlay, (0, 0, 0, 22), (0, y), (VIEW_W, y))
    view_surface.blit(overlay, (0, 0))


def draw_text(surface, text, pos, color=(0, 0, 0)):
    font = pygame.font.SysFont("Arial", FONT_SIZE, bold=True)
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=pos)
    surface.blit(surf, rect)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Drone — приціл у центрі, стрілки = огляд")
    clock = pygame.time.Clock()

    cam = Camera(WORLD_W / 2, WORLD_H / 2)
    target = Target(WORLD_W / 2, WORLD_H / 2)
    auto_mode = False
    stage = "normal"
    show_target_txt = False

    run = True
    while run:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if stage == "destroyed":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    run = False
            elif event.type == pygame.KEYDOWN:
                if not auto_mode:
                    if event.key == pygame.K_q:
                        cam.speed_kmh = min(
                            cam.speed_kmh + DRONE_SPEED_STEP, DRONE_MAX_SPEED_KMH
                        )
                    if event.key == pygame.K_a:
                        cam.speed_kmh = max(
                            cam.speed_kmh - DRONE_SPEED_STEP, DRONE_MIN_SPEED_KMH
                        )
                if event.key == pygame.K_SPACE:
                    if show_target_txt and stage != "destroyed":
                        auto_mode = not auto_mode
                        stage = "locked" if auto_mode else "normal"

        if stage != "destroyed":
            if not auto_mode:
                cam.update_manual(pygame.key.get_pressed(), dt)
            else:
                cam.update_auto(target, dt)
            target.update(dt, cam.x, cam.y)

            inside = target.is_inside_square(cam.x, cam.y, SQUARE_SIZE)
            big = target.covers_half_square(SQUARE_SIZE)
            if inside and big and stage != "locked" and not auto_mode:
                show_target_txt = True
            elif inside and big and auto_mode:
                show_target_txt = True
            else:
                show_target_txt = False

            if target.covers_whole_view():
                stage = "destroyed"
                auto_mode = False

        draw_monitor_frame(screen)
        view = screen.subsurface(SCREEN_RECT)
        view.fill(SKY_COLOR)

        grid_c = (100, 140, 170)
        off_x = (-cam.x + VIEW_CX) % 80
        off_y = (-cam.y + VIEW_CY) % 80
        for gx in range(int(off_x), VIEW_W + 80, 80):
            pygame.draw.line(view, grid_c, (gx, 0), (gx, VIEW_H), 1)
        for gy in range(int(off_y), VIEW_H + 80, 80):
            pygame.draw.line(view, grid_c, (0, gy), (VIEW_W, gy), 1)

        target.draw(view, cam.x, cam.y)
        draw_scanlines(view)
        draw_crosshair_fixed(view, (VIEW_CX, VIEW_CY))

        hud_y = SCREEN_RECT.bottom + 14
        font = pygame.font.SysFont("Arial", 20)
        hint = font.render(
            "Стрілки — зсув огляду  Q/A — швидкість  Пробіл — автосупровід (після захоплення)",
            True,
            (200, 200, 210),
        )
        screen.blit(hint, (BEZEL_SIDE, hud_y))

        if stage == "destroyed":
            draw_text(
                screen,
                "Target Destroy",
                (WIDTH // 2, HEIGHT // 2 - 40),
                (255, 30, 30),
            )
            draw_text(
                screen,
                "Enter to exit",
                (WIDTH // 2, HEIGHT // 2 + 20),
                (0, 0, 0),
            )
        elif show_target_txt:
            if not auto_mode:
                draw_text(
                    screen,
                    "Target",
                    (WIDTH // 2, SCREEN_RECT.bottom - 8),
                    (30, 90, 30),
                )
            else:
                draw_text(
                    screen,
                    "Target Locked",
                    (WIDTH // 2, SCREEN_RECT.bottom - 8),
                    (10, 30, 150),
                )

        font2 = pygame.font.SysFont("Arial", 22)
        s1 = font2.render(
            f"Огляд (камера): {cam.speed_kmh:.0f} км/год",
            True,
            (40, 10, 10),
        )
        s2 = font2.render(
            f"Ціль: {TARGET_SPEED_KMH} км/год (хаотичний курс)",
            True,
            (40, 10, 10),
        )
        screen.blit(s1, (SCREEN_RECT.left + 6, SCREEN_RECT.top + 6))
        screen.blit(s2, (SCREEN_RECT.left + 6, SCREEN_RECT.top + 30))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
