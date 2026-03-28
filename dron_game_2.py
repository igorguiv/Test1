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
DRONE_SPEED_PX_PER_S = DRONE_MIN_SPEED_KMH * 1000 / 3600 * (1/3)  # аналогічне масштабування

AUTO_ACQUIRE_MARGIN = 20  # запас по центрування (в пікселях)

FONT_SIZE = 30

# Функція малює силует "шахеда"
def draw_shahed(surface, center, size):
    # size — це загальна висота, пропорції відносно
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
    def __init__(self, cx, cy):
        self.x = cx + random.randint(-100,100)
        self.y = cy + random.randint(-100,100)
        self.dir_angle = random.uniform(0, 2*math.pi)
        self.turn_vel = 0
        self.size = TARGET_INITIAL_SIZE
        self.base_size = TARGET_INITIAL_SIZE
        self.dist_px = 230 # для обрахунку масштабу
        self.speed_px = TARGET_SPEED_PX_PER_S
        self.last_change = 0

    def update(self, dt, cross_x, cross_y):
        # Ціль намагається тікати від прицілу, плавно змінюючи напрям
        vec_x = self.x - cross_x
        vec_y = self.y - cross_y
        if vec_x == 0 and vec_y == 0:
            vec_x = 1
        desired_angle = math.atan2(vec_y, vec_x)
        # Плавна зміна напряму до "away"
        diff = (desired_angle - self.dir_angle + math.pi) % (2*math.pi) - math.pi
        self.dir_angle += diff * 0.03
        # Додаємо невеликий випадковий "дрифт"
        if random.random() < 0.05:
            self.dir_angle += random.uniform(-0.2,0.2)
        # Рух цілі
        self.x += self.speed_px * math.cos(self.dir_angle) * dt
        self.y += self.speed_px * math.sin(self.dir_angle) * dt

        # Відбивання від меж екрану
        if not (0 < self.x < WIDTH): self.dir_angle += math.pi
        if not (0 < self.y < HEIGHT): self.dir_angle += math.pi

        # Оновлення дистанції для масштабу
        self.dist_px = math.hypot(self.x - cross_x, self.y - cross_y)
        # Масштабуємо розмір - що ближче ціль, то більша
        self.size = int(self.base_size * 200 / max(80, self.dist_px))

    def draw(self, surface):
        draw_shahed(surface, (int(self.x), int(self.y)), self.size)

    def is_inside_square(self, cross_x, cross_y, square_size):
        # Перевіряє, чи центр цілі у квадраті прицілу
        hs = square_size // 2
        return (cross_x - hs <= self.x <= cross_x + hs) and (cross_y - hs <= self.y <= cross_y + hs)

    def covers_half_square(self, square_size):
        # Чи займає ціль принаймні половину квадрата прицілу
        return self.size >= square_size // 2

    def covers_whole_screen(self):
        # Чи займає ціль увесь екран
        return self.size >= max(WIDTH, HEIGHT) * 1.2

# Клас дрона/прицілу
class Drone:
    def __init__(self, cx, cy):
        self.x = cx
        self.y = cy
        self.speed_kmh = DRONE_MIN_SPEED_KMH
        self.manual = True  # Якщо True — ручне керування, якщо False — автосупровід
        self.speed_px = DRONE_SPEED_PX_PER_S

    def speed_px_value(self):
        # Повертає швидкість у пікселях/сек
        return self.speed_kmh * 1000 / 3600 * (1/3)

    def update_manual(self, keys_pressed, dt):
        # Ручне керування прицілом
        dx, dy = 0, 0
        if keys_pressed[pygame.K_LEFT]:
            dx -= 1
        if keys_pressed[pygame.K_RIGHT]:
            dx += 1
        if keys_pressed[pygame.K_UP]:
            dy -= 1
        if keys_pressed[pygame.K_DOWN]:
            dy += 1
        norm = math.hypot(dx, dy)
        if norm != 0:
            dx /= norm
            dy /= norm
            move = self.speed_px_value() * dt
            self.x += dx * move
            self.y += dy * move

        # Обмежуємо координати вікном
        self.x = min(max(self.x, 0), WIDTH)
        self.y = min(max(self.y, 0), HEIGHT)

    def update_auto(self, target: Target, dt):
        # Автоматичне наближення прицілу до цілі
        dx = target.x - self.x
        dy = target.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 2:
            dx /= dist
            dy /= dist
            self.x += dx * self.speed_px_value() * dt
            self.y += dy * self.speed_px_value() * dt

        # Автоматична зміна швидкості для швидшого суміщення
        if dist > 280:
            self.speed_kmh = DRONE_MAX_SPEED_KMH
        elif dist < 110:
            self.speed_kmh = DRONE_MIN_SPEED_KMH
        else:
            scale = (dist - 110) / (280-110)
            self.speed_kmh = int(DRONE_MIN_SPEED_KMH + (DRONE_MAX_SPEED_KMH - DRONE_MIN_SPEED_KMH) * scale)

        self.x = min(max(self.x, 0), WIDTH)
        self.y = min(max(self.y, 0), HEIGHT)

    def center(self):
        return int(self.x), int(self.y)

# Малюємо приціл: червоний квадрат та зелена точка в центрі
def draw_crosshair(surface, center):
    x, y = center
    hs = SQUARE_SIZE // 2
    # Червоний квадрат
    pygame.draw.rect(surface, SQUARE_COLOR,
                     (x - hs, y - hs, SQUARE_SIZE, SQUARE_SIZE),
                     2)
    # Зелена крапка
    pygame.draw.circle(surface, CROSSHAIR_COLOR, (x, y), CROSSHAIR_RADIUS)

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

    center = (WIDTH//2, HEIGHT//2)
    drone = Drone(*center)
    target = Target(WIDTH//2, HEIGHT//2)
    auto_mode = False
    stage = "normal"  # Також можливі 'locked' або 'destroyed'
    show_target_txt = False

    run = True
    while run:
        dt = clock.tick(FPS)/1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if stage == 'destroyed':
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    run = False
            elif event.type == pygame.KEYDOWN:
                if not auto_mode:
                    # Зміна швидкості дрона клавішами 'q'/'a'
                    if event.key == pygame.K_q:
                        drone.speed_kmh = min(drone.speed_kmh+DRONE_SPEED_STEP, DRONE_MAX_SPEED_KMH)
                    if event.key == pygame.K_a:
                        drone.speed_kmh = max(drone.speed_kmh-DRONE_SPEED_STEP, DRONE_MIN_SPEED_KMH)
                if event.key == pygame.K_SPACE:
                    # Вмикаємо/вимикаємо автосупровід, якщо ціль захоплена
                    if show_target_txt and stage != 'destroyed':
                        auto_mode = not auto_mode
                        if auto_mode:
                            stage = 'locked'
                        else:
                            stage = 'normal'

        if stage == "destroyed":
            # Фіксуємо все, очікуємо ENTER
            pass
        else:
            cross_x, cross_y = drone.center()
            if not auto_mode:
                keys = pygame.key.get_pressed()
                drone.update_manual(keys, dt)
            else:
                drone.update_auto(target, dt)

            target.update(dt, cross_x, cross_y)

            # Перевіряємо: чи ціль у прицілі і вона достатньо велика (займає півквадрата)
            inside = target.is_inside_square(cross_x, cross_y, SQUARE_SIZE)
            big = target.covers_half_square(SQUARE_SIZE)
            if inside and big and not stage == 'locked' and not auto_mode:
                show_target_txt = True
            elif inside and big and auto_mode:
                show_target_txt = True
                # У режимі авто швидкість змінюється
            else:
                show_target_txt = False

            # Якщо ціль займала екран — перемагаємо
            if target.covers_whole_screen():
                stage = "destroyed"
                auto_mode = False

        # --- МАЛЮВАННЯ ---
        screen.fill(SKY_COLOR)
        target.draw(screen)
        draw_crosshair(screen, drone.center())

        # Написи
        if stage == "destroyed":
            draw_text(screen, "Target Destroy", (WIDTH//2, HEIGHT//2-40), (255,30,30))
            draw_text(screen, "Enter to exit", (WIDTH//2, HEIGHT//2+20), (0,0,0))
        elif show_target_txt:
            if not auto_mode:
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
    main()
