import pygame
import sys
import random
import math

# --- Константи ---
WIDTH, HEIGHT = 800, 600
FPS = 60

SKY_COLOR = (135, 206, 235)
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

# Функція малює силует "шахеда"
def draw_shahed(surface, center, size):
    x, y = center
    w = size * 1.5
    h = size
    # Тіло
    pygame.draw.polygon(surface, TARGET_COLOR, [
        (x - 0.2*w, y + 0.4*h),
        (x + 0.2*w, y + 0.4*h),
        (x + 0.3*w, y),
        (x, y - 0.4*h),
        (x - 0.3*w, y),
    ], TARGET_OUTLINE_WIDTH)
    # Крила
    pygame.draw.line(surface, TARGET_COLOR, (x - 0.6*w, y + 0.15*h), (x + 0.6*w, y + 0.15*h), TARGET_OUTLINE_WIDTH)
    # Хвіст
    pygame.draw.line(surface, TARGET_COLOR, (x, y + 0.4*h), (x, y + 0.6*h), TARGET_OUTLINE_WIDTH)
    # Пропелер
    pygame.draw.line(surface, TARGET_COLOR, (x, y - 0.37*h), (x, y - 0.46*h), TARGET_OUTLINE_WIDTH)

# Клас цілі (шахед)
class Target:
    def __init__(self):
        # Ініціалізуємо цільовий об'єкт біля центру екрану
        self.x = WIDTH // 2 + random.randint(-80, 80)
        self.y = HEIGHT // 2 + random.randint(-80, 80)
        self.dir_angle = random.uniform(0, 2*math.pi)
        self.size = TARGET_INITIAL_SIZE
        self.base_size = TARGET_INITIAL_SIZE
        self.drift_timer = 0
        self.dir_vel = 0
        self.chng_time = 0
        self.base_target_speed = TARGET_SPEED_PX_PER_S
        # Для ефекту "тікає від центру"
        self.fake_dist = 220  # фейкова дистанція

    def update(self, dt, drone_speed_px, drone_dir):  # drone_dir – tuple(dx,dy)
        # --- Здвиг напрямку у випадковий бік, але з загальною тенденцією тікати від центру ---
        cx, cy = WIDTH // 2, HEIGHT // 2
        vec_x = self.x - cx
        vec_y = self.y - cy
        if vec_x == 0 and vec_y == 0:
            vec_x = 0.1
        away_angle = math.atan2(vec_y, vec_x)
        # Трохи "хаотично" — із зміною напряму
        if self.chng_time <= 0:
            # Раз на ~0.7-1.5 секунди трохи міняємо напрямок у випадковий бік
            delta = random.uniform(-0.5, 0.5)
            self.dir_angle += delta
            self.chng_time = random.uniform(0.7, 1.5)
        else:
            self.chng_time -= dt
        
        # Зміщуємо основний напрямок із поточним "вектором втечі"
        diff = (away_angle - self.dir_angle + math.pi) % (2*math.pi) - math.pi
        self.dir_angle += diff * 0.07

        # Перелічуємо швидкість
        speed = self.base_target_speed
        # Трохи шуму в бік (для "хаотичності")
        drift_x = math.sin(pygame.time.get_ticks()/1017.0) * 40
        drift_y = math.sin(pygame.time.get_ticks()/853.0) * 40

        self.x += (speed * math.cos(self.dir_angle) + drift_x) * dt
        self.y += (speed * math.sin(self.dir_angle) + drift_y) * dt

        # Відсутня взаємодія із прицілом напряму; тікає від центру!

        # Відбивання від меж екрану
        margin = self.size // 2 + 10
        if not (margin < self.x < WIDTH-margin):
            self.dir_angle = math.pi - self.dir_angle
            self.x = min(max(self.x, margin), WIDTH-margin)
        if not (margin < self.y < HEIGHT-margin):
            self.dir_angle = -self.dir_angle
            self.y = min(max(self.y, margin), HEIGHT-margin)

        # Обчислюємо "відстань" до центру (по суті — для масштабу)
        self.fake_dist = math.hypot(self.x - cx, self.y - cy)
        if self.fake_dist < 70: self.fake_dist = 70  # мінімальна дистанція

        # Зміна розміру у залежності від дистанції (наближення до центру!)
        self.size = int(self.base_size * 200 / max(70, self.fake_dist))

    def draw(self, surface):
        draw_shahed(surface, (int(self.x), int(self.y)), self.size)

    def is_inside_square(self):
        # Перевіряє, чи ціль повністю у квадраті прицілу (що завжди по центру)
        # Перевіряємо чи центр цілі у квадраті + чи її контур вкладається
        cx, cy = WIDTH // 2, HEIGHT // 2
        hs = SQUARE_SIZE // 2
        return (
            (cx - hs <= self.x <= cx + hs) and
            (cy - hs <= self.y <= cy + hs) and
            (self.x - self.size*0.8 >= cx - hs) and (self.x + self.size*0.8 <= cx + hs) and
            (self.y - self.size*0.8 >= cy - hs) and (self.y + self.size*0.8 <= cy + hs)
        )

    def covers_half_square(self):
        # Чи займає ціль принаймні половину квадрата прицілу
        return self.size >= SQUARE_SIZE // 2

    def covers_whole_screen(self):
        # Чи займає ціль увесь екран
        return self.size >= max(WIDTH, HEIGHT) * 1.2

# Клас дрона — лише швидкість та напрямок, положення завжди в центрі!
class Drone:
    def __init__(self):
        self.speed_kmh = DRONE_MIN_SPEED_KMH
        self.dir = [0, 0]  # напрямок (dx, dy), нормований
        self.auto_mode = False

    def speed_px_value(self):
        return self.speed_kmh * 1000 / 3600 * (1/3)

    def manual_update(self, keys_pressed):
        dx, dy = 0, 0
        if keys_pressed[pygame.K_LEFT]:  dx -= 1
        if keys_pressed[pygame.K_RIGHT]: dx += 1
        if keys_pressed[pygame.K_UP]:    dy -= 1
        if keys_pressed[pygame.K_DOWN]:  dy += 1
        norm = math.hypot(dx, dy)
        if norm != 0:
            self.dir[0] = dx / norm
            self.dir[1] = dy / norm
        else:
            self.dir = [0, 0]

    def auto_update(self, target: Target):
        # Вектор від центру до цілі
        cx, cy = WIDTH//2, HEIGHT//2
        dx = target.x - cx
        dy = target.y - cy
        dist = math.hypot(dx, dy)
        if dist > 2:
            self.dir = [dx/dist, dy/dist]
        else:
            self.dir = [0,0]
        # Автозміна швидкості для ефективного наближення — залишаємо можливість ручної зміни
        # (Користувач все одно може вручну змінити кілометраж!)

    def move_target(self, target: Target, dt):
        # Зсуваємо ціль відносно центру на "швидкість прицілу"
        # (Змінюємо тим самим ефективну відстань до цілі)
        # Ціль "тікає", приціл "наздоганяє" (ефект досягається додаванням швидкості прицілу до координат цілі)
        target.x -= self.dir[0] * self.speed_px_value() * dt * 1.3  # "дрібний бонус" до швидкості
        target.y -= self.dir[1] * self.speed_px_value() * dt * 1.3

# Малюємо приціл — квадрат та зелена крапка у центрі екрана
def draw_crosshair(surface):
    cx, cy = WIDTH //2, HEIGHT //2
    hs = SQUARE_SIZE // 2
    # Червоний квадрат
    pygame.draw.rect(surface, SQUARE_COLOR, (cx - hs, cy - hs, SQUARE_SIZE, SQUARE_SIZE), 2)
    # Зелена крапка
    pygame.draw.circle(surface, CROSSHAIR_COLOR, (cx, cy), CROSSHAIR_RADIUS)

# Функція для тексту на екрані
def draw_text(surface, text, pos, color=(0,0,0)):
    font = pygame.font.SysFont("Arial", FONT_SIZE, bold=True)
    text_surface = font.render(text, True, color)
    rect = text_surface.get_rect(center=pos)
    surface.blit(text_surface, rect)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Drone Targeting Simulator")
    clock = pygame.time.Clock()

    drone = Drone()
    target = Target()
    stage = "normal" # 'normal', 'locked', 'destroyed'
    show_target_txt = False

    running = True
    while running:
        dt = clock.tick(FPS)/1000
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if stage == "destroyed":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    running = False
            elif event.type == pygame.KEYDOWN:
                # Зміна швидкості дрона завжди дозволена!
                if event.key == pygame.K_q:
                    drone.speed_kmh = min(drone.speed_kmh+DRONE_SPEED_STEP, DRONE_MAX_SPEED_KMH)
                if event.key == pygame.K_a:
                    drone.speed_kmh = max(drone.speed_kmh-DRONE_SPEED_STEP, DRONE_MIN_SPEED_KMH)
                if event.key == pygame.K_SPACE:
                    # Вмикаємо/вимикаємо автосупровід, якщо ціль захоплена
                    if show_target_txt and stage != 'destroyed':
                        drone.auto_mode = not drone.auto_mode
                        if drone.auto_mode:
                            stage = 'locked'
                        else:
                            stage = 'normal'

        if stage == "destroyed":
            # Все фіксуємо, очікуємо ENTER
            pass
        else:
            if not drone.auto_mode:
                drone.manual_update(keys)
            else:
                drone.auto_update(target)

            # Приціл завжди у центрі. Зсуваємо ціль відносно центру на швидкість прицілу.
            drone.move_target(target, dt)
            # Оновлюємо рух самої цілі (хаотична втеча)
            target.update(dt, drone.speed_px_value(), drone.dir)

            # Перевіряємо стан захвату
            inside = target.is_inside_square()
            big = target.covers_half_square()
            show_target_txt = inside and big

            if target.covers_whole_screen():
                stage = "destroyed"
                drone.dir = [0,0]
                drone.auto_mode = False

        # --- МАЛЮВАННЯ ---
        screen.fill(SKY_COLOR)
        target.draw(screen)
        draw_crosshair(screen)

        # Написи
        if stage == "destroyed":
            draw_text(screen, "Target Destroy", (WIDTH//2, HEIGHT//2-40), (255,30,30))
            draw_text(screen, "Enter to exit", (WIDTH//2, HEIGHT//2+20), (0,0,0))
        elif show_target_txt:
            if not drone.auto_mode:
                draw_text(screen, "Target", (WIDTH//2, HEIGHT//2 + SQUARE_SIZE//2 + 25), (30,90,30))
            else:
                draw_text(screen, "Target Locked", (WIDTH//2, HEIGHT//2 + SQUARE_SIZE//2 + 25), (10,30,150))

        # Виводимо швидкість дрона і цілі
        font = pygame.font.SysFont("Arial", 22)
        s1 = font.render(f"Drone speed: {drone.speed_kmh:.0f} км/год", True, (40, 10, 10))
        s2 = font.render(f"Target speed: {TARGET_SPEED_KMH} км/год", True, (40, 10, 10))
        screen.blit(s1, (10,10))
        screen.blit(s2, (10, 38))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
