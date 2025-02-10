import pyxel
import random
import math
from typing import List, Callable, Tuple

# Configuration du jeu et des ressources
class GameConfig:
    WINDOW_WIDTH = 160               # largeur de la fenêtre en pixels
    WINDOW_HEIGHT = 120              # hauteur de la fenêtre en pixels
    MAP_WIDTH = 256                  # nombre de tuiles en largeur
    MAP_HEIGHT = 256                 # nombre de tuiles en hauteur
    TILE_SIZE = 8                    # taille d'une tuile en pixels

    PLAYER_SPEED = 1.2               # vitesse de déplacement du joueur
    BULLET_SPEED = 3                 # vitesse des balles
    RELOAD_TIME = 10                 # temps de rechargement entre deux tirs (en frames)

    SHIELD_DURATION = 60             # durée d'activation du bouclier (en frames)
    SHIELD_COOLDOWN = 60             # temps de recharge du bouclier (en frames)

    ENEMY_COUNT = 10                 # nombre d'ennemis
    ENEMY_TYPES = {"CHASER": 0, "SHOOTER": 1, "BOMBER": 2}

    # Paramètres de génération de grotte (automate cellulaire)
    INITIAL_WALL_PROBABILITY = 0.40  # probabilité initiale d'un mur
    SMOOTHING_ITERATIONS = 2         # nombre d'itérations de lissage
    SMOOTHING_THRESHOLD = 4          # seuil de voisins murs pour transformer une tuile en mur

    FLOOR_TILE = 0                   # valeur représentant le sol
    WALL_TILE = 1                    # valeur représentant un mur

    SAFE_ZONE_RADIUS = 10            # rayon (en tuiles) autour du spawn à dégager
    BULLET_COLLISION_RADIUS = 4      # seuil de collision pour les balles (en pixels)

    # Pour les décorations (herbe, pierres, fleur, etc.)
    DECORATION_PROBABILITY = 0.01    # probabilité globale d'ajouter une décoration sur une tuile de sol
    DECORATION_SPRITE_WIDTH = 7      # largeur d'une image de décoration
    DECORATION_SPRITE_HEIGHT = 7     # hauteur d'une image de décoration

    # Pour le joueur et son bouclier (sprites situés sur la deuxième rangée, y = 7)
    PLAYER_SPRITE_X = 0              # abscisse du sprite de l'homme dans le fichier ressource
    PLAYER_SPRITE_Y = 7              # ordonnée du sprite de l'homme
    PLAYER_SPRITE_WIDTH = 7          # largeur du sprite de l'homme
    PLAYER_SPRITE_HEIGHT = 7         # hauteur du sprite de l'homme

    SHIELD_SPRITE_X = 7              # abscisse du sprite du bouclier dans le fichier ressource
    SHIELD_SPRITE_Y = 7              # ordonnée du sprite du bouclier
    SHIELD_SPRITE_WIDTH = 7          # largeur du sprite du bouclier
    SHIELD_SPRITE_HEIGHT = 7         # hauteur du sprite du bouclier

    # Pour le bouclier qui tourne autour du joueur
    SHIELD_ORBIT_RADIUS = 8          # distance (en pixels) entre le joueur et le bouclier lorsqu'il tourne

# --- Classes de base (Entity, Player, Bullet, Enemy) ---

class Entity:
    def __init__(self, x: float, y: float, speed: float):
        # initialisation de l'entité
        self.x = x
        self.y = y
        self.speed = speed

    def move(self, dx: float, dy: float) -> None:
        # déplacement sans vérification de collision
        self.x += dx
        self.y += dy

    def move_with_collision(self, dx: float, dy: float, is_walkable: Callable[[float, float], bool]) -> None:
        # déplacement en x puis en y avec vérification de collision
        new_x = self.x + dx
        if is_walkable(new_x, self.y):
            self.x = new_x
        new_y = self.y + dy
        if is_walkable(self.x, new_y):
            self.y = new_y

class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, GameConfig.PLAYER_SPEED)
        self.hp = 3
        self.shield_active = False
        self.shield_timer = 0
        self.shield_cooldown = 0
        self.reload_timer = 0
        self.shield_angle = 0  # angle (en radians) pour la rotation du bouclier

    def update(self, is_walkable: Callable[[float, float], bool]) -> None:
        dx = dy = 0
        if pyxel.btn(pyxel.KEY_Z):
            dy -= self.speed
        if pyxel.btn(pyxel.KEY_S):
            dy += self.speed
        if pyxel.btn(pyxel.KEY_Q):
            dx -= self.speed
        if pyxel.btn(pyxel.KEY_D):
            dx += self.speed
        self.move_with_collision(dx, dy, is_walkable)

        # Activation du bouclier au clic droit si le cooldown est terminé
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) and self.shield_cooldown == 0:
            self.activate_shield()

        if self.shield_active:
            self.shield_timer -= 1
            # mettre à jour l'angle pour faire tourner le bouclier autour du joueur
            self.shield_angle = (self.shield_angle + 0.1) % (2 * math.pi)
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_cooldown = GameConfig.SHIELD_COOLDOWN
        elif self.shield_cooldown > 0:
            self.shield_cooldown -= 1

        if self.reload_timer > 0:
            self.reload_timer -= 1

    def activate_shield(self) -> None:
        self.shield_active = True
        self.shield_timer = GameConfig.SHIELD_DURATION

    def can_shoot(self) -> bool:
        return self.reload_timer == 0

    def shoot(self) -> None:
        self.reload_timer = GameConfig.RELOAD_TIME

class Bullet(Entity):
    def __init__(self, x: float, y: float, vx: float, vy: float, owner: str):
        super().__init__(x, y, GameConfig.BULLET_SPEED)
        self.vx = vx
        self.vy = vy
        self.active = True
        self.owner = owner

    def update(self, is_walkable: Callable[[float, float], bool]) -> None:
        self.move_with_collision(self.vx, self.vy, is_walkable)
        if (self.x < 0 or self.x >= GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE or
            self.y < 0 or self.y >= GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE):
            self.active = False
        if not is_walkable(self.x, self.y):
            self.active = False

class Enemy(Entity):
    def __init__(self, x: float, y: float, etype: int):
        speed = 0.5 if etype == GameConfig.ENEMY_TYPES["CHASER"] else 0.3
        super().__init__(x, y, speed)
        self.etype = etype
        self.hp = 2
        self.reload_timer = 60

    def update(self, player: Player, bullets: List[Bullet], is_walkable: Callable[[float, float], bool]) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            move_dx = (dx / dist) * self.speed
            move_dy = (dy / dist) * self.speed
            self.move_with_collision(move_dx, move_dy, is_walkable)
        if self.etype == GameConfig.ENEMY_TYPES["SHOOTER"]:
            if self.reload_timer <= 0:
                self.reload_timer = 60
                angle = math.atan2(dy, dx)
                bullets.append(Bullet(self.x, self.y, math.cos(angle) * 2, math.sin(angle) * 2, "enemy"))
        elif self.etype == GameConfig.ENEMY_TYPES["BOMBER"]:
            if dist < 8 or self.reload_timer <= 0:
                if dist < 16 and not player.shield_active:
                    # logique d'explosion éventuelle
                    pass
                self.hp = 0
        self.reload_timer -= 1

    def is_alive(self) -> bool:
        return self.hp > 0

# --- Classe Game (avec génération de carte, ennemis, décorations, etc.) ---
class Game:
    def __init__(self):
        pyxel.init(GameConfig.WINDOW_WIDTH, GameConfig.WINDOW_HEIGHT, fps=60, title="Cave Game with Decorations")
        # Charger le fichier de ressources (ressources.pyxres) qui contient tous les sprites :
        # • Sur la première rangée : décorations (herbe, pierres, fleur)
        # • Sur la deuxième rangée (y = 7) : sprite de l'homme (à (0,7)) et du bouclier (à (7,7))
        pyxel.load("ressources.pyxres")
        pyxel.mouse(True)
        self.map = self.generate_map()
        self.player_start_x = (GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE) // 2
        self.player_start_y = (GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE) // 2
        self.clear_safe_zone(self.player_start_x, self.player_start_y, GameConfig.SAFE_ZONE_RADIUS)
        self.player = Player(self.player_start_x, self.player_start_y)
        self.enemies: List[Enemy] = []
        self.generate_enemies(GameConfig.ENEMY_COUNT)
        self.bullets: List[Bullet] = []
        # Génération des décorations (par exemple, herbe, pierres, fleurs) sur le sol
        self.decorations: List[Tuple[float, float, int]] = []
        self.generate_decorations()
        pyxel.run(self.update, self.draw)

    def generate_map(self) -> List[List[int]]:
        map_grid = [
            [GameConfig.WALL_TILE if random.random() < GameConfig.INITIAL_WALL_PROBABILITY else GameConfig.FLOOR_TILE
             for _ in range(GameConfig.MAP_WIDTH)]
            for _ in range(GameConfig.MAP_HEIGHT)
        ]
        for x in range(GameConfig.MAP_WIDTH):
            map_grid[0][x] = GameConfig.WALL_TILE
            map_grid[GameConfig.MAP_HEIGHT - 1][x] = GameConfig.WALL_TILE
        for y in range(GameConfig.MAP_HEIGHT):
            map_grid[y][0] = GameConfig.WALL_TILE
            map_grid[y][GameConfig.MAP_WIDTH - 1] = GameConfig.WALL_TILE
        for _ in range(GameConfig.SMOOTHING_ITERATIONS):
            new_map = [[GameConfig.FLOOR_TILE for _ in range(GameConfig.MAP_WIDTH)] for _ in range(GameConfig.MAP_HEIGHT)]
            for y in range(1, GameConfig.MAP_HEIGHT - 1):
                for x in range(1, GameConfig.MAP_WIDTH - 1):
                    wall_count = 0
                    for j in range(-1, 2):
                        for i in range(-1, 2):
                            if i == 0 and j == 0:
                                continue
                            if map_grid[y + j][x + i] == GameConfig.WALL_TILE:
                                wall_count += 1
                    if wall_count >= GameConfig.SMOOTHING_THRESHOLD:
                        new_map[y][x] = GameConfig.WALL_TILE
                    else:
                        new_map[y][x] = GameConfig.FLOOR_TILE
            map_grid = new_map
        return map_grid

    def clear_safe_zone(self, center_x: float, center_y: float, radius: int) -> None:
        tile_center_x = int(center_x // GameConfig.TILE_SIZE)
        tile_center_y = int(center_y // GameConfig.TILE_SIZE)
        for y in range(max(0, tile_center_y - radius), min(GameConfig.MAP_HEIGHT, tile_center_y + radius + 1)):
            for x in range(max(0, tile_center_x - radius), min(GameConfig.MAP_WIDTH, tile_center_x + radius + 1)):
                self.map[y][x] = GameConfig.FLOOR_TILE

    def generate_enemies(self, count: int) -> None:
        attempts = 0
        while len(self.enemies) < count and attempts < count * 10:
            tile_x = random.randint(0, GameConfig.MAP_WIDTH - 1)
            tile_y = random.randint(0, GameConfig.MAP_HEIGHT - 1)
            if self.map[tile_y][tile_x] != GameConfig.FLOOR_TILE:
                attempts += 1
                continue
            x = tile_x * GameConfig.TILE_SIZE + GameConfig.TILE_SIZE // 2
            y = tile_y * GameConfig.TILE_SIZE + GameConfig.TILE_SIZE // 2
            if math.hypot(x - self.player_start_x, y - self.player_start_y) < GameConfig.SAFE_ZONE_RADIUS * GameConfig.TILE_SIZE:
                attempts += 1
                continue
            etype = random.choice(list(GameConfig.ENEMY_TYPES.values()))
            self.enemies.append(Enemy(x, y, etype))
            attempts += 1

    def generate_decorations(self) -> None:
        self.decorations = []
        for tile_y in range(GameConfig.MAP_HEIGHT):
            for tile_x in range(GameConfig.MAP_WIDTH):
                if self.map[tile_y][tile_x] == GameConfig.FLOOR_TILE:
                    if random.random() < GameConfig.DECORATION_PROBABILITY:
                        # Ici, on peut choisir un type de décoration (parmi vos dessins dans la première rangée)
                        sprite_index = random.randint(0, 3)  # par exemple, 0 à 3 pour de l'herbe
                        offset_x = (GameConfig.TILE_SIZE - GameConfig.DECORATION_SPRITE_WIDTH) // 2
                        offset_y = (GameConfig.TILE_SIZE - GameConfig.DECORATION_SPRITE_HEIGHT) // 2
                        x = tile_x * GameConfig.TILE_SIZE + offset_x
                        y = tile_y * GameConfig.TILE_SIZE + offset_y
                        self.decorations.append((x, y, sprite_index))

    def is_walkable(self, x: float, y: float) -> bool:
        if x < 0 or x >= GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE or \
           y < 0 or y >= GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE:
            return False
        tile_x = int(x // GameConfig.TILE_SIZE)
        tile_y = int(y // GameConfig.TILE_SIZE)
        return self.map[tile_y][tile_x] == GameConfig.FLOOR_TILE

    @property
    def camera_x(self) -> float:
        return max(0, min(self.player.x - GameConfig.WINDOW_WIDTH / 2,
                           GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE - GameConfig.WINDOW_WIDTH))

    @property
    def camera_y(self) -> float:
        return max(0, min(self.player.y - GameConfig.WINDOW_HEIGHT / 2,
                           GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE - GameConfig.WINDOW_HEIGHT))

    def update(self) -> None:
        self.player.update(self.is_walkable)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.player.can_shoot():
            mx = pyxel.mouse_x + self.camera_x
            my = pyxel.mouse_y + self.camera_y
            dx = mx - self.player.x
            dy = my - self.player.y
            dist = math.hypot(dx, dy)
            if dist != 0:
                vx = (dx / dist) * GameConfig.BULLET_SPEED
                vy = (dy / dist) * GameConfig.BULLET_SPEED
                self.bullets.append(Bullet(self.player.x, self.player.y, vx, vy, "player"))
            self.player.shoot()

        for bullet in self.bullets:
            bullet.update(self.is_walkable)
        for bullet in self.bullets:
            if not bullet.active:
                continue
            if bullet.owner == "player":
                for enemy in self.enemies:
                    if enemy.is_alive() and math.hypot(bullet.x - enemy.x, bullet.y - enemy.y) < GameConfig.BULLET_COLLISION_RADIUS:
                        enemy.hp -= 1
                        bullet.active = False
                        break
            elif bullet.owner == "enemy":
                if math.hypot(bullet.x - self.player.x, bullet.y - self.player.y) < GameConfig.BULLET_COLLISION_RADIUS:
                    bullet.active = False
                    if not self.player.shield_active:
                        self.player.hp -= 1
        self.bullets = [b for b in self.bullets if b.active]

        for enemy in self.enemies:
            enemy.update(self.player, self.bullets, self.is_walkable)
        self.enemies = [e for e in self.enemies if e.is_alive()]

        if self.player.hp <= 0:
            pyxel.quit()

    def draw(self) -> None:
        pyxel.cls(0)
        start_tile_x = int(self.camera_x // GameConfig.TILE_SIZE)
        start_tile_y = int(self.camera_y // GameConfig.TILE_SIZE)
        end_tile_x = start_tile_x + (GameConfig.WINDOW_WIDTH // GameConfig.TILE_SIZE) + 2
        end_tile_y = start_tile_y + (GameConfig.WINDOW_HEIGHT // GameConfig.TILE_SIZE) + 2
        for ty in range(start_tile_y, min(end_tile_y, GameConfig.MAP_HEIGHT)):
            for tx in range(start_tile_x, min(end_tile_x, GameConfig.MAP_WIDTH)):
                tile = self.map[ty][tx]
                color = 3 if tile == GameConfig.FLOOR_TILE else 8
                px = tx * GameConfig.TILE_SIZE - self.camera_x
                py_pos = ty * GameConfig.TILE_SIZE - self.camera_y
                pyxel.rect(px, py_pos, GameConfig.TILE_SIZE, GameConfig.TILE_SIZE, color)

        # Dessin des décorations
        for deco in self.decorations:
            x, y, sprite_index = deco
            if (x + GameConfig.DECORATION_SPRITE_WIDTH >= self.camera_x and 
                x < self.camera_x + GameConfig.WINDOW_WIDTH and
                y + GameConfig.DECORATION_SPRITE_HEIGHT >= self.camera_y and 
                y < self.camera_y + GameConfig.WINDOW_HEIGHT):
                src_x = sprite_index * GameConfig.DECORATION_SPRITE_WIDTH
                src_y = 0
                pyxel.blt(x - self.camera_x, y - self.camera_y,
                          0, src_x, src_y,
                          GameConfig.DECORATION_SPRITE_WIDTH, GameConfig.DECORATION_SPRITE_HEIGHT,
                          0)

        # Dessin des ennemis et des balles
        for enemy in self.enemies:
            pyxel.circ(enemy.x - self.camera_x, enemy.y - self.camera_y, 3, 8)
        for bullet in self.bullets:
            pyxel.rect(bullet.x - self.camera_x - 1, bullet.y - self.camera_y - 1, 2, 2, 7)

        # Dessin du joueur (sprite de l'homme)
        # On centre le sprite sur la position du joueur.
        player_draw_x = self.player.x - self.camera_x - GameConfig.PLAYER_SPRITE_WIDTH // 2
        player_draw_y = self.player.y - self.camera_y - GameConfig.PLAYER_SPRITE_HEIGHT // 2
        pyxel.blt(player_draw_x, player_draw_y,
                  0,
                  GameConfig.PLAYER_SPRITE_X, GameConfig.PLAYER_SPRITE_Y,
                  GameConfig.PLAYER_SPRITE_WIDTH, GameConfig.PLAYER_SPRITE_HEIGHT,
                  0)

        # Dessin du bouclier (s'il est activé) qui tourne autour du joueur
        if self.player.shield_active:
            radius = GameConfig.SHIELD_ORBIT_RADIUS
            shield_x = self.player.x + radius * math.cos(self.player.shield_angle)
            shield_y = self.player.y + radius * math.sin(self.player.shield_angle)
            shield_draw_x = shield_x - self.camera_x - GameConfig.SHIELD_SPRITE_WIDTH // 2
            shield_draw_y = shield_y - self.camera_y - GameConfig.SHIELD_SPRITE_HEIGHT // 2
            pyxel.blt(shield_draw_x, shield_draw_y,
                      0,
                      GameConfig.SHIELD_SPRITE_X, GameConfig.SHIELD_SPRITE_Y,
                      GameConfig.SHIELD_SPRITE_WIDTH, GameConfig.SHIELD_SPRITE_HEIGHT,
                      0)

        # Affichage des informations
        pyxel.text(5, 5, f"hp: {self.player.hp}", 7)
        shield_status = "actif" if self.player.shield_active else (f"cooldown: {self.player.shield_cooldown}" if self.player.shield_cooldown > 0 else "disponible")
        pyxel.text(5, 15, f"bouclier: {shield_status}", 7)
        pyxel.text(5, 25, f"ennemis: {len(self.enemies)}", 7)

if __name__ == "__main__":
    Game()
