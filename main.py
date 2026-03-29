import pgzrun
from pgzhelper import * 
import random
import os
import math

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pgzero.builtins import Actor, keyboard, screen, clock, keys, mouse, Rect, animate

# --- Настройки окна ---
os.environ['SDL_VIDEO_CENTERED'] = '1' 
WIDTH = 800
HEIGHT = 600
TITLE = "Unpathetic Hell"
TILE_SIZE = 32

# --- Игровые константы и состояние ---
ALL_UPGRADES = [
    {"id": "speed", "name": "Wind Walker", "desc": "+1 Скорость передвижения"},
    {"id": "hp_max", "name": "Titan Heart", "desc": "+50 к макс. HP и полный отхил"},
    {"id": "dmg", "name": "Sharpened Steel", "desc": "+0.5 к урону меча"},
    {"id": "knock", "name": "Force Push", "desc": "+100 к силе отброса мечом"},
    {"id": "range", "name": "Long Reach", "desc": "+30 к радиусу удара мечом"},
    {"id": "vampire", "name": "Vampirism", "desc": "10% шанс восстановить 2 HP при убийстве"},
    {"id": "bullet_dmg", "name": "Heavy Slugs", "desc": "Пули наносят больше урона"}
]

# Объекты игрока
hero = Actor('hero1', (WIDTH // 2, HEIGHT // 2))
hero.speed = 4  #по дефолту 4
hero.hp = 100 #по дефолту 100
hero.recovery_timer = 0 # по дефолту 0
hero.images = ['hero1','hero2','hero1','hero3']
hero.fps = 10

# Игровые переменные
game_mode = "menu" # "menu", "game", "guide", "story", "lose", "win"
weapon_mode = "sword"
show_upgrade_screen = False
flash_timer = 0

# Характеристики оружия
sword_dmg = 2 # по дефолту 1
sword_range = 200 #по дефолту 300
sword_cooldown = 0 #по дефолту 0
SWORD_SPEED = 300   #Кадры в секундах по дефолту 120
KNOCKBACK_POWER = 200 # по дефолту 200
player_bullets_dmg = 1 # по дефолту 1
vampire_chance = 0 # по дефолту 0.1

# Прогрессия
waves = 1
parts_collected = 0
kills_in_current_wave = 0
total_wave_enemies = 10  
enemy_base_health = 3
spawn_timer = 0
spawn_delay = 120
boss_spawned = False
boss_timer = 0
void_pulling = False
void_timer = 0

# Списки объектов
enemies = []
bullets = []
upgrade_options = []

# Кнопки меню
play_button = Rect(300, 200, 200, 50)
guide_button = Rect(300, 280, 200, 50)
story_button = Rect(300, 360, 200, 50)
exit_button = Rect(300, 440, 200, 50)

# Кнопка вернутся
back_button = Rect(20, 530, 100, 40)

# Кнопка для проигрыша
exit_to_menu_button = Rect(300, 420, 200, 50)
retry_button = Rect(300, 350, 200, 50)

# Кнопка для паузы
resume_button = Rect(300, 200, 200, 50)

# ---------------------------------------------------------
# Вспомогательные функции (Utility)
# ---------------------------------------------------------



def create_bullet(target_pos, is_boss=False, origin_pos=None):
    start_pos = origin_pos if origin_pos else hero.pos
    image_name = 'bullet_tank' if is_boss else 'bullet_hero'
    
    bullet = Actor(image_name, start_pos)
    angle_rad = math.radians(bullet.angle_to(target_pos))
    speed = 5 if is_boss else 10 # Сделаем пули боссов чуть быстрее 4
    
    # ВСЕГДА используем минус для vy в Pygame Zero
    bullet.vx = speed * math.cos(angle_rad)
    bullet.vy = -speed * math.sin(angle_rad) 
    
    bullet.angle = bullet.angle_to(target_pos)
    bullet.is_boss_bullet = is_boss
    bullets.append(bullet)
    start_pos = origin_pos if origin_pos else hero.pos
    
    # ВЫБОР КАРТИНКИ:
    # Игрок стреляет обычной 'bullet', боссы — 'boss_bullet'
    image_name = 'bullet_tank' if is_boss else 'bullet_hero'
    
    bullet = Actor(image_name, start_pos)
    angle_rad = math.radians(bullet.angle_to(target_pos))
    speed = 4 if is_boss else 10
    
    bullet.vx = speed * math.cos(angle_rad)
    # Исправляем направление для боссов и игрока
    bullet.vy = -speed * math.sin(angle_rad) if not is_boss else speed * math.sin(angle_rad)
    
    bullet.angle = bullet.angle_to(target_pos)
    bullet.is_boss_bullet = is_boss
    bullets.append(bullet)

def apply_upgrade(upgrade):
    global show_upgrade_screen, sword_dmg, sword_range, vampire_chance, KNOCKBACK_POWER, player_bullets_dmg
    if upgrade['id'] == "speed": hero.speed += 1
    elif upgrade['id'] == "hp_max": hero.hp = 100 
    elif upgrade['id'] == "dmg": sword_dmg += 1.5
    elif upgrade['id'] == "knock": KNOCKBACK_POWER += 100
    elif upgrade['id'] == "range": sword_range += 50
    elif upgrade['id'] == "vampire": vampire_chance += 0.1
    elif upgrade['id'] == "bullet_dmg": player_bullets_dmg += 1
    show_upgrade_screen = False

# ---------------------------------------------------------
# Логика Боссов (Boss Patterns)
# ---------------------------------------------------------

def handle_boss_behavior(b):
    global boss_timer, void_pulling, void_timer
    boss_timer += 1
    
    if b.type == "SLASHER":
        # Слэшер теперь быстрее (2 пикселя) и делает рывок каждые 70 кадров вместо 90
        if boss_timer % 90 == 0:
            animate(b, tween='decelerate', duration=0.4, x=hero.x, y=hero.y)
        elif not any(a.running for a in getattr(b, '_animations', [])):
            b.x += 2 if b.x < hero.x else -2
            b.y += 2 if b.y < hero.y else -2

    elif b.type == "SPAWNER":
        # Хаотичное движение
        b.x += (1 if b.x < hero.x else -1) + random.uniform(-2, 2)
        b.y += (1 if b.y < hero.y else -1) + random.uniform(-2, 2)
        
        # Инициализируем счетчик прихвостней, если его еще нет
        if not hasattr(b, 'minion_count'):
            b.minion_count = 0
            b.max_minions = 10 # Лимит одновременно существующих слуг

        if boss_timer % 100 == 0 and b.minion_count < b.max_minions:
            for _ in range(2): # Призываем по 2 за раз
                if b.minion_count >= b.max_minions: break
                
                # Выбираем: спавнить у босса или у края карты
                if random.random() < 0.5:
                    # У босса
                    pos = (b.x + random.randint(-50, 50), b.y + 50)
                else:
                    # У границ карты (как в обычных волнах)
                    side = random.choice(['t', 'b', 'l', 'r'])
                    pos = {
                        't': (random.randint(0, WIDTH), -50), 
                        'b': (random.randint(0, WIDTH), HEIGHT+50),
                        'l': (-50, random.randint(0, HEIGHT)), 
                        'r': (WIDTH+50, random.randint(0, HEIGHT))
                    }[side]

                m = Actor(random.choice(['enemy','enemy2']), pos)
                m.health = 2 + (waves // 10)
                m.max_health = m.health
                m.parent_boss = b # Привязываем слугу к боссу
                enemies.append(m)
                b.minion_count += 1

    elif b.type == "TANK":
        # Цикл: 720 кадров (~12 сек)
        # 0-300: Обычный бой
        # 300-420: Пауза
        # 420-720: Вращение пуль
        phase_timer = boss_timer % 720 

        if phase_timer < 300:
            # ФАЗА 1: Обычное движение и БОЛЬШЕ пуль
            if b.distance_to(hero) > 200:
                b.x += 0.5 if b.x < hero.x else -0.5
                b.y += 0.5 if b.y < hero.y else -0.5
            
            # Стреляем чаще (раз в 30 кадров) и большим количеством пуль (шаг 30 градусов)
            if boss_timer % 30 == 0:
                for angle in range(0, 360, 30): # Было 45, стало 30 — пуль стало больше
                    rad = math.radians(angle)
                    create_bullet((b.x + math.cos(rad), b.y + math.sin(rad)), True, b.pos)

        elif 300 <= phase_timer < 420:
            # ФАЗА 2: Остановка перед "ураганом"
            pass 

        elif 420 <= phase_timer < 720:
            # ФАЗА 3: Вращающийся крест (веер по вертикали и горизонтали)
            # rotation_offset создает эффект вращения по часовой стрелке
            rotation_offset = (boss_timer * 5) 
            
            if boss_timer % 10 == 0:
                # Вместо range(0, 360, 30) используем список фиксированных углов "креста"
                # Это 0 (право), 90 (низ), 180 (лево), 270 (верх)
                for base_angle in [0, 90, 180, 270]:
                    # Прибавляем rotation_offset к каждому базовому углу
                    rad = math.radians(base_angle + rotation_offset)
                    create_bullet((b.x + math.cos(rad), b.y + math.sin(rad)), True, b.pos)

    elif b.type == "VOID":
        void_timer += 1
        # Фазы: 250 кадров обычная, 150 кадров притяжение
        if not void_pulling and void_timer >= 250:
            void_pulling, void_timer = True, 0
        elif void_pulling and void_timer >= 90:
            void_pulling, void_timer = False, 0

        # ДВИЖЕНИЕ: Скорость 1.5 (преследует игрока)
        b.x += 1.5 if b.x < hero.x else -1.5
        b.y += 1.5 if b.y < hero.y else -1.5

        # ЛОГИКА ПРИТЯЖЕНИЯ
        if void_pulling:
            dist = b.distance_to(hero)
            if dist > 30:
                hero.x += (b.x - hero.x) * 0.04
                hero.y += (b.y - hero.y) * 0.04
        
        # СТРЕЛЬБА:
        # Выбираем темп стрельбы: 12 (очень быстро) при втягивании, 30 (нормально) в покое
        shoot_rate = 12 if void_pulling else 20
        
        if boss_timer % shoot_rate == 0:
            if void_pulling:
                # Если притягивает, добавляем разброс (например, в радиусе 50 пикселей)
                inaccurate_pos = (
                    hero.x + random.randint(-100, 100),
                    hero.y + random.randint(-100, 100)
                )
                create_bullet(inaccurate_pos, True, b.pos)
            else:
                # В обычной фазе стреляет точно
                create_bullet(hero.pos, True, b.pos)
    b.x = max(50, min(WIDTH - 50, b.x))
    b.y = max(50, min(HEIGHT - 50, b.y))

# ---------------------------------------------------------
# Игровая логика (Core Engine)
# ---------------------------------------------------------

def player_update():
    hero.is_move = False  # Сбрасываем флаг перед проверкой кнопок

    # Используем маленькие буквы (a, d, w, s)
    if keyboard.A and hero.left > 0:
        hero.x -= hero.speed
        hero.flip_x = True
    elif keyboard.D and hero.right < WIDTH:
        hero.x += hero.speed
        hero.flip_x = False

    if keyboard.W and hero.top > 0:
        hero.y -= hero.speed 
    elif keyboard.S and hero.bottom < HEIGHT:
        hero.y += hero.speed


    if keyboard.W or keyboard.A or keyboard.S or keyboard.D:
        hero.is_move = True
    else:
        hero.is_move = False
    # Исправленное название метода со скобками
    if hero.is_move:
        hero.animate()
    else:
        hero.image = 'hero1'

def enemy_update():
    global flash_timer
    if hero.recovery_timer > 0: hero.recovery_timer -= 1

    for e in enemies[:]:
        if getattr(e, 'is_boss', False):
            e.flip_x = e.x > hero.x
            handle_boss_behavior(e)
        else:
            e.x += 1 if e.x < hero.x else -1
            e.y += 1 if e.y < hero.y else -1
            e.flip_x = e.x > hero.x
        
        if hero.recovery_timer <= 0:
            collision = False
            # Проверка типа врага для честного урона
            if getattr(e, 'type', "") == "TANK":
                if e.distance_to(hero) < 60: # Урон только вблизи центра
                    collision = True
            else:
                collision = hero.colliderect(e)

            if collision:
                hero.hp -= 5
                hero.recovery_timer = 40 
                flash_timer = 5
                
                # Отброс игрока (только от обычных врагов)
                if not getattr(e, 'is_boss', False):
                    dx, dy = hero.x - e.x, hero.y - e.y
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 0:
                        tx = max(50, min(WIDTH-50, hero.x + (dx/dist)*100))
                        ty = max(50, min(HEIGHT-50, hero.y + (dy/dist)*100))
                        animate(hero, tween='decelerate', duration=0.25, x=tx, y=ty)

def bullet_update():
    for b in bullets[:]:
        b.x += b.vx
        b.y += b.vy
        
        if getattr(b, 'is_boss_bullet', False):
            if b.colliderect(hero):
                hero.hp -= 10
                if b in bullets: bullets.remove(b)
        else:
            for e in enemies[:]:
                if b.colliderect(e):
                    e.health -= player_bullets_dmg
                    if b in bullets: bullets.remove(b)
                    check_death(e)
        
        if not (0 < b.x < WIDTH and 0 < b.y < HEIGHT):
            if b in bullets: bullets.remove(b)

def check_death(e):
    global parts_collected, game_mode, flash_timer
    if e.health <= 0:
        if hasattr(e, 'parent_boss'):
            e.parent_boss.minion_count -= 1


        if e in enemies: enemies.remove(e)
        parts_collected += 1

        if random.random() < vampire_chance and hero.hp < 100: 
            hero.hp = min(100, hero.hp + 2)
 
        if getattr(e, 'is_boss', False):
            flash_timer = 15
            if getattr(e, 'type', "") == "VOID":
                game_mode = "win"
                enemies.clear()
                bullets.clear()

def spawn_system():
    global spawn_timer, kills_in_current_wave, boss_spawned, spawn_delay, total_wave_enemies, waves, upgrade_options, show_upgrade_screen

    # 1. Проверка завершения волны и подготовка магазина
    if kills_in_current_wave >= total_wave_enemies and not enemies:
        if waves < 100:
            waves += 1
            kills_in_current_wave = 0
            boss_spawned = False
            
            if waves % 5 == 0:
                # Фильтруем способности
                available_pool = []
                for upg in ALL_UPGRADES:
                    # Если ХП полно, убираем Titan Heart (hp_max)
                    if upg['id'] == "hp_max" and hero.hp >= 100:
                        continue
                    available_pool.append(upg)

                # Назначаем веса (шансы): обычные - 10, редкие - 2
                weights = []
                for upg in available_pool:
                    if upg['id'] == "vampire":
                        weights.append(7)  # Чуть меньше, чем у остальных (будет редким, но возможным)
                    elif upg['id'] in ["dmg", "range"]:
                        weights.append(11) # Меч выпадает чуть чаще, как ты просил
                    else:
                        weights.append(10) # Обычный шанс для остальных навыков

                # Выбираем 3 уникальных улучшения
                upgrade_options = []
                temp_pool = list(available_pool)
                temp_weights = list(weights)
                
                for _ in range(min(3, len(temp_pool))):
                    chosen = random.choices(temp_pool, weights=temp_weights, k=1)[0]
                    upgrade_options.append(chosen)
                    idx = temp_pool.index(chosen)
                    temp_pool.pop(idx)
                    temp_weights.pop(idx)

                show_upgrade_screen = True
            
            # Усложнение количества врагов в волне
            if waves >= 10:
                spawn_delay, total_wave_enemies = 180, 15 + (waves // 2)
            else:
                total_wave_enemies += 2

    if hero.hp <= 0: return

    # 2. Логика появления БОССОВ
    if waves % 25 == 0 and not boss_spawned:
        boss_spawned = True
        # Удали эту строку, если хочешь, чтобы во время босса лезли и обычные мобы:
        kills_in_current_wave = total_wave_enemies 
        
        data = [
            None, 
            ('slasher', "SLASHER", 300, "XENO-SLASHER"),
            ('spawner', "SPAWNER", 500, "THE BROODMOTHER"),
            ('tank', "TANK", 1000, "SIEGE MECH"),
            ('void', "VOID", 2000, "VOID HEART")
        ]
        b_idx = min(waves // 25, len(data) - 1)
        img, b_type, hp, name = data[b_idx]
        
        boss = Actor(img, (WIDTH//2, -100))
        boss.type, boss.max_health, boss.health, boss.name, boss.is_boss = b_type, hp, hp, name, True
        enemies.append(boss)
        animate(boss, y=150, duration=2, tween='decelerate')
    
    # 3. Логика появления ОБЫЧНЫХ ВРАГОВ (Группами)
    elif kills_in_current_wave < total_wave_enemies and not boss_spawned:
        spawn_timer -= 1
        if spawn_timer <= 0:
            # Расчет размера группы по твоей формуле
            if waves <= 50:
                # Плавный рост до 20 к 50-й волне
                calculated_size = 1 + int(waves * 0.38)
                max_allowed = min(calculated_size, 20)
            else:
                # После 50 волны: +1 враг каждые 5 уровней
                max_allowed = 20 + ((waves - 50) // 5)
            
            remaining = total_wave_enemies - kills_in_current_wave
            group_size = min(max_allowed, remaining)

            for _ in range(group_size):
                side = random.choice(['t', 'b', 'l', 'r'])
                pos = {
                    't': (random.randint(0, WIDTH), -50), 
                    'b': (random.randint(0, WIDTH), HEIGHT+50),
                    'l': (-50, random.randint(0, HEIGHT)), 
                    'r': (WIDTH+50, random.randint(0, HEIGHT))
                }[side]
                
                en = Actor(random.choice(["enemy","enemy2"]), pos)
                en.health = enemy_base_health + (waves // 5)
                en.max_health = en.health
                en.is_boss = False
                enemies.append(en)
                kills_in_current_wave += 1
            
            spawn_timer = spawn_delay

def reset_game():
    # Объявляем ВСЕ переменные, которые меняем
    global game_mode, weapon_mode, show_upgrade_screen, waves, parts_collected
    global kills_in_current_wave, total_wave_enemies, enemy_base_health
    global spawn_timer, spawn_delay, boss_spawned, boss_timer
    global void_pulling, void_timer, upgrade_options
    global player_bullets_dmg, vampire_chance
    global sword_dmg, sword_range, sword_cooldown, KNOCKBACK_POWER

    # 1. Сброс состояния героя
    hero.hp = 100
    hero.pos = (WIDTH // 2, HEIGHT // 2)
    hero.recovery_timer = 0
    
    # 2. Режимы
    game_mode = "game"
    weapon_mode = "sword"
    show_upgrade_screen = False

    # 3. Характеристики оружия (твои дефолты)
    sword_dmg = 2
    sword_range = 200
    sword_cooldown = 0
    KNOCKBACK_POWER = 200
    player_bullets_dmg = 1
    vampire_chance = 0 

    # 4. Прогрессия
    waves = 1
    parts_collected = 0
    kills_in_current_wave = 0
    total_wave_enemies = 10  
    enemy_base_health = 3
    spawn_timer = 0
    spawn_delay = 120
    boss_spawned = False
    boss_timer = 0
    void_pulling = False
    void_timer = 0

    # 5. Очистка списков (ВАЖНО использовать .clear())
    enemies.clear()
    bullets.clear()
    upgrade_options.clear()

# ---------------------------------------------------------
# Обработка ввода (Input)
# ---------------------------------------------------------

def on_key_down(key):
    global weapon_mode, game_mode

    if key == keys.ESCAPE:
        if game_mode == "game":
            game_mode = "pause"
        elif game_mode == "pause":
            game_mode = "game"

    if show_upgrade_screen:
        for i in range(len(upgrade_options)):
            if key == getattr(keys, f'K_{i+1}'): 
                apply_upgrade(upgrade_options[i])
    elif game_mode == "game":
        if key == keys.K_1: weapon_mode = "sword"
        if key == keys.K_2: weapon_mode = "gun"



def on_mouse_down(pos, button):
    global sword_cooldown, game_mode
    
    # Левый клик мыши
    if button == mouse.LEFT:
        
        # 1. ЛОГИКА ГЛАВНОГО МЕНЮ
        if game_mode == "menu":
            if play_button.collidepoint(pos): 
                reset_game()  # Запускаем чистую игру
            elif guide_button.collidepoint(pos): 
                game_mode = "guide"
            elif story_button.collidepoint(pos): 
                game_mode = "story"
            elif exit_button.collidepoint(pos):
                sys.exit()
        
        # 2. ЛОГИКА ПАУЗЫ (новые кнопки)
        elif game_mode == "pause":
            if resume_button.collidepoint(pos): 
                game_mode = "game"
            elif guide_button.collidepoint(pos): 
                game_mode = "guide"
            elif story_button.collidepoint(pos): 
                game_mode = "story"
        
        # 3. ЛОГИКА ЭКРАНА ПРОИГРЫША
        elif game_mode == "lose":
            if retry_button.collidepoint(pos): 
                reset_game()  # Полный сброс характеристик и врагов
            elif exit_to_menu_button.collidepoint(pos): 
                game_mode = "menu"
        
        # 4. ВЫХОД ИЗ ГАЙДА / ИСТОРИИ
        elif game_mode in ["guide", "story"] and back_button.collidepoint(pos):
            # Если игра уже запущена (есть волны или враги), возвращаемся в паузу, иначе в меню
            if waves > 1 or enemies:
                game_mode = "pause"
            else:
                game_mode = "menu"
        
        # 5. ИГРОВОЙ ПРОЦЕСС (Атака)
        elif game_mode == "game" and hero.hp > 0:
            if weapon_mode == "gun":
                create_bullet(pos)
            elif weapon_mode == "sword" and sword_cooldown <= 0:
                for e in enemies[:]:
                    if hero.distance_to(e) < sword_range:
                        e.health -= sword_dmg
                        dx, dy = e.x - hero.x, e.y - hero.y
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist > 0:
                            tx = max(50, min(WIDTH-50, e.x + (dx/dist)*KNOCKBACK_POWER))
                            ty = max(50, min(HEIGHT-50, e.y + (dy/dist)*KNOCKBACK_POWER))
                            animate(e, tween='decelerate', duration=0.3, x=tx, y=ty)
                        check_death(e)
                sword_cooldown = SWORD_SPEED

# ---------------------------------------------------------
# Отрисовка (Rendering)
# ---------------------------------------------------------

def draw():
    screen.clear()
    
    # 1. Фон (Тайлинг камня)
    for x in range(0, WIDTH, TILE_SIZE):
        for y in range(0, HEIGHT, TILE_SIZE):
            screen.blit('stone', (x, y))

    # 2. Главное меню
    if game_mode == "menu":
        screen.draw.text("UNPATHETIC HELL", center=(WIDTH//2, 100), fontsize=70, color="gold", shadow=(2,2))
        
        # Список кнопок: (объект_прямоугольника, текст)
        menu_items = [
            (play_button, "ИГРАТЬ"),
            (guide_button, "ГАЙД"),
            (story_button, "ПРЕДЫСТОРИЯ"),
            (exit_button, "ВЫХОД")
        ]
        
        for btn, text in menu_items:
            # Рисуем фон кнопки
            color = (80, 45, 45) if text == "ВЫХОД" else (45, 50, 80)
            screen.draw.filled_rect(btn, color)
            screen.draw.rect(btn, "cyan")
            screen.draw.text(text, center=btn.center, fontsize=30, color="white")

    # 3. Игровой процесс
    elif game_mode == "game":
        hero.draw()
        current_boss = None
        
        for e in enemies:
            e.draw()
            if getattr(e, 'is_boss', False): 
                current_boss = e
            elif hasattr(e, 'max_health') and e.health < e.max_health:
                # Полоска здоровья обычных мобов
                screen.draw.filled_rect(Rect(e.x-20, e.y-40, 40, 5), "black")
                screen.draw.filled_rect(Rect(e.x-20, e.y-40, 40 * (e.health/e.max_health), 5), "#45E960")

        # UI Босса (внизу экрана)
        if current_boss:
            ratio = max(0, current_boss.health / current_boss.max_health)
            screen.draw.filled_rect(Rect(100, HEIGHT-50, 600, 20), "black")
            screen.draw.filled_rect(Rect(100, HEIGHT-50, 600 * ratio, 20), "#E94560")
            screen.draw.text(current_boss.name, center=(WIDTH//2, HEIGHT-65), fontsize=20)

        for b in bullets: 
            b.draw()
            
        # Общий UI игрока
        screen.draw.text(f"HP: {int(hero.hp)} | Оружие: {weapon_mode.upper()}", (20, 20), fontsize=30)
        screen.draw.text(f"Волна: {waves} | Убийства: {parts_collected}", (WIDTH-250, 20), fontsize=30)
        
        # --- Блок характеристик (под HP) ---
        stats_y = 50
        if hero.speed > 4:
            screen.draw.text(f"• Speed: {hero.speed}", (20, stats_y), fontsize=20, color="lightblue")
            stats_y += 20
        if sword_dmg > 2:
            screen.draw.text(f"• Sword DMG: {sword_dmg}", (20, stats_y), fontsize=20, color="orange")
            stats_y += 20
        if player_bullets_dmg > 1:
            screen.draw.text(f"• Bullet DMG: {player_bullets_dmg}", (20, stats_y), fontsize=20, color="yellow")
            stats_y += 20
        if vampire_chance > 0:
            screen.draw.text(f"• Vampirism: {int(vampire_chance * 100)}%", (20, stats_y), fontsize=20, color="red")
            stats_y += 20
        if KNOCKBACK_POWER > 200:
            screen.draw.text(f"• Knockback: {KNOCKBACK_POWER}", (20, stats_y), fontsize=20, color="lightgreen")
            stats_y += 20

    # 4. Экраны Справки и Истории
    elif game_mode == "guide":
        screen.draw.text("КРАТКИЙ ГАЙД", center=(WIDTH//2, 50), fontsize=50, color="cyan")
        guide_text = ("""
            WASD - Передвижение героем
            MOUSE LEFT - Атака (мечом или пушкой)
            KEY 1 - Выбрать меч
            KEY 2 - Выбрать пушку
            Уничтожь врагов и собери части вышки.
            Каждые 5 волн ты можешь прокачаться.
            Каждые 25 волн появляются боссы, будь аккуратен!
        """)
        screen.draw.text(guide_text, (100, 150), fontsize=30, color="white")

    elif game_mode == "story":
        screen.draw.text("ПРЕДЫСТОРИЯ", center=(WIDTH//2, 50), fontsize=50, color="gold")
        story_text = ('''
            Вы оказались на планете Qb-18380,
            где вас застала врасплох внезапно напавшая орда монстров.
            Ваша башня связи была разрушена, и теперь,
            чтобы вернуться домой, вам предстоит преодолеть 100 волн хаоса
            и отнять квантовые резонаторы у боссов.
            Установите связь, найдите путь назад.
            Удачи!

        ''')
        screen.draw.text(story_text, (60, 150), fontsize=28, color="white", lineheight=1.5)

    # 5. Финальные экраны
    elif game_mode == "win":
        screen.draw.text("ТЫ СВАЛИЛ С ЭТОЙ ПЛАНЕТЫ!", center=(WIDTH//2, HEIGHT//2), fontsize=60, color="gold")
        
    elif game_mode == "pause":
        screen.draw.filled_rect(Rect(0, 0, WIDTH, HEIGHT), (0, 0, 0, 150)) # Затемнение
        screen.draw.text("ПАУЗА", center=(WIDTH//2, 100), fontsize=60, color="white")
        for btn, text in [(resume_button, "ПРОДОЛЖИТЬ"), (guide_button, "ГАЙД"), (story_button, "ИСТОРИЯ")]:
            screen.draw.filled_rect(btn, (45, 50, 80))
            screen.draw.text(text, center=btn.center, fontsize=30)

    elif game_mode == "lose":
        screen.draw.text("ИГРА ОКОНЧЕНА, ЛУЗЕР!", center=(WIDTH//2, 200), fontsize=80, color="red")
        # Кнопки проигрыша
        for btn, text in [(retry_button, "ЗАНОВО"), (exit_to_menu_button, "В МЕНЮ")]:
            screen.draw.filled_rect(btn, (80, 45, 45))
            screen.draw.text(text, center=btn.center, fontsize=30)
    
    # Кнопка назад для текстовых режимов
    if game_mode in ["guide", "story"]:
        screen.draw.filled_rect(back_button, (80, 45, 45))
        screen.draw.rect(back_button, "white")
        screen.draw.text("BACK", center=back_button.center, color="white")

    # 6. Оверлей улучшений (Level Up)
    if show_upgrade_screen:
        screen.draw.filled_rect(Rect(0, 0, WIDTH, HEIGHT), (20, 20, 30, 220)) # Затемнение
        screen.draw.text("ВЫБЕРИ УЛУЧШЕНИЕ!", center=(WIDTH//2, 60), fontsize=60, color="gold")
        
        for i, opt in enumerate(upgrade_options):
            rect = Rect(150, 130 + i * 140, 500, 110)
            screen.draw.filled_rect(rect, (45, 50, 80))
            screen.draw.rect(rect, "cyan")
            screen.draw.text(opt["name"], (170, 145 + i * 140), fontsize=40, color="gold")
            screen.draw.text(opt["desc"], (170, 190 + i * 140), fontsize=25, color="white")
            screen.draw.text(f"[{i+1}]", (600, 170 + i * 140), fontsize=30, color="cyan")

def update(dt):
    global sword_cooldown, game_mode
    if show_upgrade_screen or game_mode != "game": return
    if hero.hp > 100:
        hero.hp = 100
    player_update()
    enemy_update()
    bullet_update()
    spawn_system()
    if sword_cooldown > 0: sword_cooldown -= 1
    if hero.hp <= 0: game_mode = "lose"

pgzrun.go()