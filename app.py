import pyxel
import random
import math
from typing import Callable, List

class GameConfig:
    # configuration du jeu
    WINDOW_WIDTH = 160
    WINDOW_HEIGHT = 120
    MAP_WIDTH = 256      # en nombre de tuiles
    MAP_HEIGHT = 256     # en nombre de tuiles
    TILE_SIZE = 8        # taille d'une tuile en pixels
    PLAYER_SPEED = 1.2
    BULLET_SPEED = 3
    SHIELD_DURATION = 30
    RELOAD_TIME = 10
    ENEMY_COUNT = 10
    ENEMY_TYPES = {"CHASER": 0, "SHOOTER": 1, "BOMBER": 2}
    WALL_PROBABILITY = 0.2    # probabilité qu'une tuile soit un mur
    SAFE_ZONE_RADIUS = 10     # rayon en tuiles autour du spawn à dégager
    FLOOR_TILE = 0            # valeur représentant le sol
    WALL_TILE = 1             # valeur représentant un mur

class Entity:
    def __init__(self, x: float, y: float, speed: float):
        """
        initialisation de l'entité
        :param x: position en x (pixels)
        :param y: position en y (pixels)
        :param speed: vitesse de déplacement
        """
        self.x = x
        self.y = y
        self.speed = speed

    def move(self, dx: float, dy: float) -> None:
        # déplacement sans vérification de collision
        self.x += dx
        self.y += dy

    def move_with_collision(self, dx: float, dy: float, is_walkable: Callable[[float, float], bool]) -> None:
        # déplacement avec vérification de collision en séparant les axes
        new_x = self.x + dx
        if is_walkable(new_x, self.y):
            self.x = new_x
        # sinon, la position x reste inchangée

        new_y = self.y + dy
        if is_walkable(self.x, new_y):
            self.y = new_y
        # sinon, la position y reste inchangée

class Player(Entity):
    def __init__(self, x: float, y: float):
        # initialisation du joueur avec bouclier et temps de rechargement
        super().__init__(x, y, GameConfig.PLAYER_SPEED)
        self.shield_active = False
        self.shield_timer = 0
        self.reload_timer = 0

    def update(self, is_walkable: Callable[[float, float], bool]) -> None:
        # mise à jour du joueur : déplacement et actions (activation du bouclier, rechargement)
        dx = dy = 0
        if pyxel.btn(pyxel.KEY_Z):  # déplacement vers le haut
            dy -= self.speed
        if pyxel.btn(pyxel.KEY_S):  # déplacement vers le bas
            dy += self.speed
        if pyxel.btn(pyxel.KEY_Q):  # déplacement vers la gauche
            dx -= self.speed
        if pyxel.btn(pyxel.KEY_D):  # déplacement vers la droite
            dx += self.speed

        # déplacement avec vérification de collision
        self.move_with_collision(dx, dy, is_walkable)

        # activation du bouclier avec le clic droit de la souris
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.activate_shield()

        # mise à jour du bouclier
        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False

        # mise à jour du rechargement
        if self.reload_timer > 0:
            self.reload_timer -= 1

    def activate_shield(self) -> None:
        # activation du bouclier du joueur
        self.shield_active = True
        self.shield_timer = GameConfig.SHIELD_DURATION

    def can_shoot(self) -> bool:
        # vérification si le joueur peut tirer (rechargement terminé)
        return self.reload_timer == 0

    def shoot(self) -> None:
        # mise à jour du rechargement après un tir
        self.reload_timer = GameConfig.RELOAD_TIME

class Bullet(Entity):
    def __init__(self, x: float, y: float, vx: float, vy: float):
        # initialisation de la balle avec sa direction et son état actif
        super().__init__(x, y, GameConfig.BULLET_SPEED)
        self.vx = vx
        self.vy = vy
        self.active = True

    def update(self, is_walkable: Callable[[float, float], bool]) -> None:
        # mise à jour de la balle : déplacement et désactivation en cas de collision avec un mur ou en dehors de la map
        self.move_with_collision(self.vx, self.vy, is_walkable)
        # désactivation si la balle sort de la map
        if (self.x < 0 or self.x >= GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE or
            self.y < 0 or self.y >= GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE):
            self.active = False
        # désactivation si la balle se trouve sur un mur
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
        # mise à jour de l'ennemi : déplacement vers le joueur et comportement spécifique au type
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            # déplacement vers le joueur en normalisant le vecteur direction
            move_dx = (dx / dist) * self.speed
            move_dy = (dy / dist) * self.speed
            self.move_with_collision(move_dx, move_dy, is_walkable)

        # comportement selon le type d'ennemi
        if self.etype == GameConfig.ENEMY_TYPES["SHOOTER"]:
            if self.reload_timer <= 0:
                self.reload_timer = 60
                angle = math.atan2(dy, dx)
                # création d'une balle tirée vers le joueur
                bullets.append(Bullet(self.x, self.y, math.cos(angle) * 2, math.sin(angle) * 2))
        elif self.etype == GameConfig.ENEMY_TYPES["BOMBER"]:
            # l'ennemi explose s'il est très proche du joueur ou si le temps est écoulé
            if dist < 8 or self.reload_timer <= 0:
                if dist < 16 and not player.shield_active:
                    # logique d'explosion (à implémenter : par exemple, infliger des dégâts au joueur)
                    pass
                self.hp = 0  # l'ennemi explose et est supprimé

        self.reload_timer -= 1

    def is_alive(self) -> bool:
        # retourne vrai si l'ennemi est encore vivant
        return self.hp > 0

class Game:
    def __init__(self):
        # initialisation de pyxel et des composants du jeu
        pyxel.init(GameConfig.WINDOW_WIDTH, GameConfig.WINDOW_HEIGHT, fps=60, title="Jeu avec map aléatoire")
        pyxel.mouse(True)
        # génération de la map aléatoire
        self.map = self.generate_map()
        # position de départ du joueur (centre de la map en pixels)
        self.player = Player((GameConfig.MAP_WIDTH * GameConfig.TILE_SIZE) // 2,
                             (GameConfig.MAP_HEIGHT * GameConfig.TILE_SIZE) // 2)
        # dégagement de la zone de spawn du joueur
        self.clear_safe_zone(self.player.x, self.player.y, GameConfig.SAFE_ZONE_RADIUS)
        # génération des ennemis sur des tuiles de sol éloignées du joueur
        self.enemies: List[Enemy] = []
        self.generate_enemies(GameConfig.ENEMY_COUNT)
        self.bullets: List[Bullet] = []
        pyxel.run(self.update, self.draw)

    def generate_map(self) -> List[List[int]]:
        # génération d'une map aléatoire sous forme de grille (0: sol, 1: mur)
        return [
            [GameConfig.WALL_TILE if random.random() < GameConfig.WALL_PROBABILITY else GameConfig.FLOOR_TILE
             for _ in range(GameConfig.MAP_WIDTH)]
            for _ in range(GameConfig.MAP_HEIGHT)
        ]

    def clear_safe_zone(self, center_x: float, center_y: float, radius: int) -> None:
        # efface les murs autour du centre pour créer une zone sûre
        tile_center_x = int(center_x // GameConfig.TILE_SIZE)
        tile_center_y = int(center_y // GameConfig.TILE_SIZE)
        for y in range(max(0, tile_center_y - radius), min(GameConfig.MAP_HEIGHT, tile_center_y + radius + 1)):
            for x in range(max(0, tile_center_x - radius), min(GameConfig.MAP_WIDTH, tile_center_x + radius + 1)):
                self.map[y][x] = GameConfig.FLOOR_TILE

    def generate_enemies(self, count: int) -> None:
        # génération d'ennemis sur des tuiles de sol et éloignés du joueur
        attempts = 0
        while len(self.enemies) < count and attempts < count * 10:
            # choix aléatoire d'une tuile
            tile_x = random.randint(0, GameConfig.MAP_WIDTH - 1)
            tile_y = random.randint(0, GameConfig.MAP_HEIGHT - 1)
            # vérification que la tuile est un sol
            if self.map[tile_y][tile_x] != GameConfig.FLOOR_TILE:
                attempts += 1
                continue
            # conversion en coordonnées pixels (centrées dans la tuile)
            x = tile_x * GameConfig.TILE_SIZE + GameConfig.TILE_SIZE // 2
            y = tile_y * GameConfig.TILE_SIZE + GameConfig.TILE_SIZE // 2
            # vérification que l'ennemi est suffisamment éloigné du joueur
            if math.hypot(x - self.player.x, y - self.player.y) < GameConfig.SAFE_ZONE_RADIUS * GameConfig.TILE_SIZE:
                attempts += 1
                continue
            etype = random.choice(list(GameConfig.ENEMY_TYPES.values()))
            self.enemies.append(Enemy(x, y, etype))
            attempts += 1

    def is_walkable(self, x: float, y: float) -> bool:
        # vérifie si la position (x, y) est marchable (correspond à un sol)
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

        # mise à jour du joueur avec gestion des collisions
        self.player.update(self.is_walkable)

        # tir du joueur avec le clic gauche de la souris
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.player.can_shoot():
            mx = pyxel.mouse_x + self.camera_x
            my = pyxel.mouse_y + self.camera_y
            dx = mx - self.player.x
            dy = my - self.player.y
            dist = math.hypot(dx, dy)
            if dist != 0:
                # normalisation du vecteur de direction pour la balle
                vx = (dx / dist) * GameConfig.BULLET_SPEED
                vy = (dy / dist) * GameConfig.BULLET_SPEED
                self.bullets.append(Bullet(self.player.x, self.player.y, vx, vy))
            self.player.shoot()

        # mise à jour des balles
        for bullet in self.bullets:
            bullet.update(self.is_walkable)
        # suppression des balles inactives
        self.bullets = [b for b in self.bullets if b.active]

        # mise à jour des ennemis
        for enemy in self.enemies:
            enemy.update(self.player, self.bullets, self.is_walkable)
        # suppression des ennemis morts
        self.enemies = [e for e in self.enemies if e.is_alive()]

    def draw(self) -> None:
        # dessin de la scène
        pyxel.cls(0)

        # dessin de la map : on affiche uniquement les tuiles visibles
        start_tile_x = int(self.camera_x // GameConfig.TILE_SIZE)
        start_tile_y = int(self.camera_y // GameConfig.TILE_SIZE)
        end_tile_x = start_tile_x + (GameConfig.WINDOW_WIDTH // GameConfig.TILE_SIZE) + 2
        end_tile_y = start_tile_y + (GameConfig.WINDOW_HEIGHT // GameConfig.TILE_SIZE) + 2

        for ty in range(start_tile_y, min(end_tile_y, GameConfig.MAP_HEIGHT)):
            for tx in range(start_tile_x, min(end_tile_x, GameConfig.MAP_WIDTH)):
                tile = self.map[ty][tx]
                # 3 pour le sol, 8 pour le mur
                color = 3 if tile == GameConfig.FLOOR_TILE else 8
                # dessin d'une tuile
                px = tx * GameConfig.TILE_SIZE - self.camera_x
                py_pos = ty * GameConfig.TILE_SIZE - self.camera_y
                pyxel.rect(px, py_pos, GameConfig.TILE_SIZE, GameConfig.TILE_SIZE, color)

        # dessin du joueur
        player_color = 9 if not self.player.shield_active else 10
        pyxel.rect(self.player.x - self.camera_x - 3, self.player.y - self.camera_y - 3, 6, 6, player_color)

        # dessin des balles
        for bullet in self.bullets:
            pyxel.rect(bullet.x - self.camera_x - 1, bullet.y - self.camera_y - 1, 2, 2, 7)

        # dessin des ennemis
        for enemy in self.enemies:
            pyxel.circ(enemy.x - self.camera_x, enemy.y - self.camera_y, 3, 8)

        # affichage d'informations utiles
        pyxel.text(5, 5, f"ennemis: {len(self.enemies)}", 7)
        pyxel.text(5, 15, f"bouclier: {'actif' if self.player.shield_active else 'inactif'}", 7)

if __name__ == "__main__":
    Game()
