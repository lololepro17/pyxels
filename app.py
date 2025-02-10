import pyxel
import random
import math
from typing import List, Callable

class GameConfig:
    # configuration du jeu
    WINDOW_WIDTH = 160               # largeur de la fenêtre en pixels
    WINDOW_HEIGHT = 120              # hauteur de la fenêtre en pixels
    MAP_WIDTH = 256                  # largeur de la carte en nombre de tuiles
    MAP_HEIGHT = 256                 # hauteur de la carte en nombre de tuiles
    TILE_SIZE = 8                    # taille d'une tuile en pixels

    PLAYER_SPEED = 1.2               # vitesse de déplacement du joueur
    BULLET_SPEED = 3                 # vitesse de la balle
    RELOAD_TIME = 10                 # temps de rechargement entre deux tirs (en frames)
    
    SHIELD_DURATION = 60             # durée d'activation du bouclier (en frames)
    SHIELD_COOLDOWN = 60             # temps de recharge du bouclier après utilisation (en frames)
    
    ENEMY_COUNT = 10                 # nombre d'ennemis
    ENEMY_TYPES = {"CHASER": 0, "SHOOTER": 1, "BOMBER": 2}

    # paramètres pour la génération de grotte (automate cellulaire)
    INITIAL_WALL_PROBABILITY = 0.45  # probabilité initiale qu'une tuile soit un mur
    SMOOTHING_ITERATIONS = 4         # nombre d'itérations de lissage
    SMOOTHING_THRESHOLD = 5          # seuil de voisins murs pour qu'une tuile devienne mur

    FLOOR_TILE = 0                   # valeur représentant le sol
    WALL_TILE = 1                    # valeur représentant un mur

    SAFE_ZONE_RADIUS = 10            # rayon (en tuiles) autour du spawn à dégager
    BULLET_COLLISION_RADIUS = 4      # seuil pour la détection de collision balle (en pixels)


class Entity:
    def __init__(self, x: float, y: float, speed: float):
        # initialisation de l'entité
        self.x = x
        self.y = y
        self.speed = speed

    def move(self, dx: float, dy: float) -> None:
        # déplacement sans gestion de collision
        self.x += dx
        self.y += dy

    def move_with_collision(self, dx: float, dy: float, is_walkable: Callable[[float, float], bool]) -> None:
        # déplacement avec vérification de collision sur chaque axe
        new_x = self.x + dx
        if is_walkable(new_x, self.y):
            self.x = new_x
        new_y = self.y + dy
        if is_walkable(self.x, new_y):
            self.y = new_y


class Player(Entity):
    def __init__(self, x: float, y: float):
        # initialisation du joueur avec points de vie, bouclier et rechargement
        super().__init__(x, y, GameConfig.PLAYER_SPEED)
        self.hp = 3                     # points de vie du joueur
        self.shield_active = False      # état du bouclier
        self.shield_timer = 0           # durée restante du bouclier
        self.shield_cooldown = 0        # temps de recharge du bouclier
        self.reload_timer = 0           # temps avant de pouvoir tirer à nouveau

    def update(self, is_walkable: Callable[[float, float], bool]) -> None:
        # mise à jour du joueur (déplacement, activation du bouclier, rechargement)
        dx = dy = 0
        if pyxel.btn(pyxel.KEY_Z):  # déplacement vers le haut
            dy -= self.speed
        if pyxel.btn(pyxel.KEY_S):  # déplacement vers le bas
            dy += self.speed
        if pyxel.btn(pyxel.KEY_Q):  # déplacement vers la gauche
            dx -= self.speed
        if pyxel.btn(pyxel.KEY_D):  # déplacement vers la droite
            dx += self.speed
        self.move_with_collision(dx, dy, is_walkable)

        # activation du bouclier au clic droit si disponible (pas en cooldown)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) and self.shield_cooldown == 0:
            self.activate_shield()

        # gestion du bouclier
        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_cooldown = GameConfig.SHIELD_COOLDOWN
        else:
            if self.shield_cooldown > 0:
                self.shield_cooldown -= 1

        # mise à jour du rechargement pour le tir
        if self.reload_timer > 0:
            self.reload_timer -= 1

    def activate_shield(self) -> None:
        # activation du bouclier si disponible
        if self.shield_cooldown == 0:
            self.shield_active = True
            self.shield_timer = GameConfig.SHIELD_DURATION

    def can_shoot(self) -> bool:
        # vérification si le joueur peut tirer
        return self.reload_timer == 0

    def shoot(self) -> None:
        # réinitialisation du temps de rechargement après un tir
        self.reload_timer = GameConfig.RELOAD_TIME


class Bullet(Entity):
    def __init__(self, x: float, y: float, vx: float, vy: float, owner: str):
        # initialisation de la balle avec direction, état actif et propriétaire ("player" ou "enemy")
        super().__init__(x, y, GameConfig.BULLET_SPEED)
        self.vx = vx
        self.vy = vy
        self.active = True
        self.owner = owner

    def update(self, is_walkable: Callable[[float, float], bool]) -> None:
        # mise à jour de la balle avec déplacement et gestion de collision avec un mur
        self.move_with_collision(self.vx, self.vy, is_walkable)
        # désactivation si la balle sort de la carte
        if (self.x < 0 or self.x >= GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE or
            self.y < 0 or self.y >= GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE):
            self.active = False
        # désactivation si la balle touche un mur
        if not is_walkable(self.x, self.y):
            self.active = False


class Enemy(Entity):
    def __init__(self, x: float, y: float, etype: int):
        # initialisation de l'ennemi avec son type, sa vitesse et ses points de vie
        speed = 0.5 if etype == GameConfig.ENEMY_TYPES["CHASER"] else 0.3
        super().__init__(x, y, speed)
        self.etype = etype
        self.hp = 2
        self.reload_timer = 60

    def update(self, player: Player, bullets: List[Bullet], is_walkable: Callable[[float, float], bool]) -> None:
        # mise à jour de l'ennemi (déplacement vers le joueur et comportement spécifique)
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            move_dx = (dx / dist) * self.speed
            move_dy = (dy / dist) * self.speed
            self.move_with_collision(move_dx, move_dy, is_walkable)

        # comportement selon le type d'ennemi
        if self.etype == GameConfig.ENEMY_TYPES["SHOOTER"]:
            if self.reload_timer <= 0:
                self.reload_timer = 60
                angle = math.atan2(dy, dx)
                # création d'une balle ennemie tirée vers le joueur
                bullets.append(Bullet(self.x, self.y, math.cos(angle) * 2, math.sin(angle) * 2, "enemy"))
        elif self.etype == GameConfig.ENEMY_TYPES["BOMBER"]:
            if dist < 8 or self.reload_timer <= 0:
                if dist < 16 and not player.shield_active:
                    # ici, on pourrait infliger des dégâts au joueur (logique d'explosion)
                    pass
                self.hp = 0  # l'ennemi explose et est supprimé

        self.reload_timer -= 1

    def is_alive(self) -> bool:
        # retourne vrai si l'ennemi est encore vivant
        return self.hp > 0


class Game:
    def __init__(self):
        # initialisation de pyxel et des composants du jeu
        pyxel.init(GameConfig.WINDOW_WIDTH, GameConfig.WINDOW_HEIGHT, fps=60, title="cave game")
        pyxel.mouse(True)
        self.map = self.generate_map()  # génération du terrain type grotte
        # position de départ du joueur (centre de la carte en pixels)
        self.player = Player((GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE) // 2,
                             (GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE) // 2)
        self.clear_safe_zone(self.player.x, self.player.y, GameConfig.SAFE_ZONE_RADIUS)
        self.enemies: List[Enemy] = []
        self.generate_enemies(GameConfig.ENEMY_COUNT)
        self.bullets: List[Bullet] = []
        pyxel.run(self.update, self.draw)

    def generate_map(self) -> List[List[int]]:
        # génération initiale aléatoire de la carte
        map_grid = [
            [GameConfig.WALL_TILE if random.random() < GameConfig.INITIAL_WALL_PROBABILITY else GameConfig.FLOOR_TILE
             for _ in range(GameConfig.MAP_WIDTH)]
            for _ in range(GameConfig.MAP_HEIGHT)
        ]
        # forcer les bords en mur
        for x in range(GameConfig.MAP_WIDTH):
            map_grid[0][x] = GameConfig.WALL_TILE
            map_grid[GameConfig.MAP_HEIGHT - 1][x] = GameConfig.WALL_TILE
        for y in range(GameConfig.MAP_HEIGHT):
            map_grid[y][0] = GameConfig.WALL_TILE
            map_grid[y][GameConfig.MAP_WIDTH - 1] = GameConfig.WALL_TILE

        # application d'itérations de lissage pour obtenir un aspect "grotte"
        for _ in range(GameConfig.SMOOTHING_ITERATIONS):
            new_map = [[GameConfig.FLOOR_TILE for _ in range(GameConfig.MAP_WIDTH)] for _ in range(GameConfig.MAP_HEIGHT)]
            for y in range(1, GameConfig.MAP_HEIGHT - 1):
                for x in range(1, GameConfig.MAP_WIDTH - 1):
                    wall_count = 0
                    # compter les murs autour de la tuile
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
        # dégagement des murs autour du spawn du joueur pour une zone sûre
        tile_center_x = int(center_x // GameConfig.TILE_SIZE)
        tile_center_y = int(center_y // GameConfig.TILE_SIZE)
        for y in range(max(0, tile_center_y - radius), min(GameConfig.MAP_HEIGHT, tile_center_y + radius + 1)):
            for x in range(max(0, tile_center_x - radius), min(GameConfig.MAP_WIDTH, tile_center_x + radius + 1)):
                self.map[y][x] = GameConfig.FLOOR_TILE

    def generate_enemies(self, count: int) -> None:
        # génération d'ennemis sur des tuiles de sol et éloignés du joueur
        attempts = 0
        while len(self.enemies) < count and attempts < count * 10:
            tile_x = random.randint(0, GameConfig.MAP_WIDTH - 1)
            tile_y = random.randint(0, GameConfig.MAP_HEIGHT - 1)
            if self.map[tile_y][tile_x] != GameConfig.FLOOR_TILE:
                attempts += 1
                continue
            # conversion en coordonnées pixels (centrées dans la tuile)
            x = tile_x * GameConfig.TILE_SIZE + GameConfig.TILE_SIZE // 2
            y = tile_y * GameConfig.TILE_SIZE + GameConfig.TILE_SIZE // 2
            if math.hypot(x - self.player.x, y - self.player.y) < GameConfig.SAFE_ZONE_RADIUS * GameConfig.TILE_SIZE:
                attempts += 1
                continue
            etype = random.choice(list(GameConfig.ENEMY_TYPES.values()))
            self.enemies.append(Enemy(x, y, etype))
            attempts += 1

    def is_walkable(self, x: float, y: float) -> bool:
        # vérifie si la position (x, y) est accessible (correspond à un sol)
        if (x < 0 or x >= GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE or
            y < 0 or y >= GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE):
            return False
        tile_x = int(x // GameConfig.TILE_SIZE)
        tile_y = int(y // GameConfig.TILE_SIZE)
        return self.map[tile_y][tile_x] == GameConfig.FLOOR_TILE

    @property
    def camera_x(self) -> float:
        # calcul de la position x de la caméra centrée sur le joueur
        return max(0, min(self.player.x - GameConfig.WINDOW_WIDTH / 2,
                           GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE - GameConfig.WINDOW_WIDTH))

    @property
    def camera_y(self) -> float:
        # calcul de la position y de la caméra centrée sur le joueur
        return max(0, min(self.player.y - GameConfig.WINDOW_HEIGHT / 2,
                           GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE - GameConfig.WINDOW_HEIGHT))

    def update(self) -> None:
        # mise à jour de la logique du jeu

        # mise à jour du joueur (déplacement, bouclier, etc.)
        self.player.update(self.is_walkable)

        # gestion du tir du joueur au clic gauche
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

        # mise à jour des balles
        for bullet in self.bullets:
            bullet.update(self.is_walkable)

        # gestion des collisions balle-ennemi et balle-joueur
        for bullet in self.bullets:
            if not bullet.active:
                continue
            if bullet.owner == "player":
                # collision entre balle du joueur et ennemi
                for enemy in self.enemies:
                    if enemy.is_alive() and math.hypot(bullet.x - enemy.x, bullet.y - enemy.y) < GameConfig.BULLET_COLLISION_RADIUS:
                        enemy.hp -= 1
                        bullet.active = False
                        break
            elif bullet.owner == "enemy":
                # collision entre balle ennemie et joueur
                if math.hypot(bullet.x - self.player.x, bullet.y - self.player.y) < GameConfig.BULLET_COLLISION_RADIUS:
                    bullet.active = False
                    if not self.player.shield_active:
                        self.player.hp -= 1

        # suppression des balles inactives
        self.bullets = [b for b in self.bullets if b.active]

        # mise à jour des ennemis
        for enemy in self.enemies:
            enemy.update(self.player, self.bullets, self.is_walkable)
        # suppression des ennemis morts
        self.enemies = [e for e in self.enemies if e.is_alive()]

        # vérification des points de vie du joueur (fin du jeu si hp <= 0)
        if self.player.hp <= 0:
            pyxel.quit()

    def draw(self) -> None:
        # dessin de la scène
        pyxel.cls(0)

        # dessin de la carte (affichage limité aux tuiles visibles)
        start_tile_x = int(self.camera_x // GameConfig.TILE_SIZE)
        start_tile_y = int(self.camera_y // GameConfig.TILE_SIZE)
        end_tile_x = start_tile_x + (GameConfig.WINDOW_WIDTH // GameConfig.TILE_SIZE) + 2
        end_tile_y = start_tile_y + (GameConfig.WINDOW_HEIGHT // GameConfig.TILE_SIZE) + 2

        for ty in range(start_tile_y, min(end_tile_y, GameConfig.MAP_HEIGHT)):
            for tx in range(start_tile_x, min(end_tile_x, GameConfig.MAP_WIDTH)):
                tile = self.map[ty][tx]
                # couleur 3 pour le sol, 8 pour le mur
                color = 3 if tile == GameConfig.FLOOR_TILE else 8
                px = tx * GameConfig.TILE_SIZE - self.camera_x
                py_pos = ty * GameConfig.TILE_SIZE - self.camera_y
                pyxel.rect(px, py_pos, GameConfig.TILE_SIZE, GameConfig.TILE_SIZE, color)

        # dessin des ennemis
        for enemy in self.enemies:
            pyxel.circ(enemy.x - self.camera_x, enemy.y - self.camera_y, 3, 8)

        # dessin des balles
        for bullet in self.bullets:
            pyxel.rect(bullet.x - self.camera_x - 1, bullet.y - self.camera_y - 1, 2, 2, 7)

        # dessin du joueur
        pyxel.rect(self.player.x - self.camera_x - 3, self.player.y - self.camera_y - 3, 6, 6, 9)

        # dessin du bouclier (affiché si actif)
        if self.player.shield_active:
            # dessin d'un cercle autour du joueur pour représenter le bouclier
            pyxel.circ(self.player.x - self.camera_x, self.player.y - self.camera_y, 8, 10)

        # affichage des informations utiles
        pyxel.text(5, 5, f"hp: {self.player.hp}", 7)
        shield_status = "actif" if self.player.shield_active else (f"cooldown: {self.player.shield_cooldown}" if self.player.shield_cooldown > 0 else "disponible")
        pyxel.text(5, 15, f"bouclier: {shield_status}", 7)
        pyxel.text(5, 25, f"ennemis: {len(self.enemies)}", 7)

if __name__ == "__main__":
    Game()
