import pyxel
import random
import math

# --- CONSTANTES GLOBALES ---

WINDOW_WIDTH = 160
WINDOW_HEIGHT = 120

MAP_WIDTH = 256     # Largeur de la map en « tuiles »
MAP_HEIGHT = 256    # Hauteur de la map en « tuiles »

TILE_SIZE = 8       # Taille d’une tuile en pixels
PLAYER_SPEED = 1.2
BULLET_SPEED = 3
SHIELD_DURATION = 30   # Durée du bouclier (en frames)
RELOAD_TIME = 10       # Intervalle minimum entre deux tirs (en frames)

# Types d’ennemis
ENEMY_TYPE_CHASER = 0
ENEMY_TYPE_SHOOTER = 1
ENEMY_TYPE_BOMBER  = 2

# ------------------------------------------------------------------
#   1) Implémentation simplifiée du Perlin Noise en Python pur
# ------------------------------------------------------------------

# Table de permutations (classique pour Perlin). On la duplique pour éviter le wrap-around.
PERM = [
    151, 160, 137, 91, 90, 15,
    131, 13, 201, 95, 96, 53, 194, 233, 7, 225, 
    140, 36, 103, 30, 69, 142, 8, 99, 37, 240, 
    21, 10, 23, 190, 6, 148, 247, 120, 234, 75, 
    0, 26, 197, 62, 94, 252, 219, 203, 117, 35, 
    11, 32, 57, 177, 33, 88, 237, 149, 56, 87, 
    174, 20, 125, 136, 171, 168,  68, 175, 74, 
    165, 71, 134, 139, 48, 27, 166, 77, 146, 158, 
    231, 83, 111, 229, 122, 60, 211, 133, 230, 
    220, 105, 92, 41, 55, 46, 245, 40, 244, 102, 
    143, 54,  65, 25,  63, 161,  1, 216, 80, 
    73, 209, 76, 132, 187, 208,  89,  18, 169, 
    200, 196, 135, 130, 116, 188, 159, 86, 164, 
    100, 109, 198, 173, 186,  3,  64,  52, 217, 
    226, 250, 124, 123,  5, 202,  38, 147, 118, 
    126, 255, 82,  85, 212, 207, 206,  59, 227, 
    47, 16,  58, 17, 182, 189, 28,  42, 223, 
    183, 170, 213, 119, 248, 152,  2,  44, 154, 
    163,  70, 221, 153, 101, 155, 167,  43, 172, 
    9, 129, 22, 39, 253,  19, 98, 108, 110, 
    79, 113, 224, 232, 178, 185, 112, 104, 218, 
    246, 97, 228, 251, 34, 242, 193, 238, 210, 
    144, 12, 191, 179, 162, 241,  81,  51, 145, 
    235, 249, 14, 239, 107,  49, 192, 214,  31, 
    181, 199, 106, 157, 184,  84, 204, 176, 115, 
    121,  50,  45, 127,  4, 150
]
# On la duplique pour simplifier l’accès (ex: p[x + 256] = p[x])
PERM = PERM + PERM

def fade(t):
    # Fonction de lissage utilisée dans le Perlin Noise
    return t * t * t * (t * (t * 6 - 15) + 10)

def lerp(a, b, t):
    return a + t * (b - a)

def grad(hash_val, x, y):
    """
    Renvoie un produit scalaire entre un vecteur gradient (déterminé par hash_val)
    et le vecteur (x, y).
    """
    # 12 correspond à 2^3 + 2^2 = 12 vecteurs possibles
    # Dans le Perlin classique 2D, on limite souvent à 8 ou 12 directions.
    h = hash_val & 3
    if h == 0:
        return  x + y
    elif h == 1:
        return -x + y
    elif h == 2:
        return  x - y
    else:  # h == 3
        return -x - y

def perlin2d(x, y):
    """
    Perlin Noise 2D pour un point (x,y) en flottant.
    x, y peuvent être n’importe quels floats. On calcule
    leur position relative dans la « cellule » la plus proche,
    puis on interpole.
    """
    # On récupère les coordonnées des cellules "de gauche" (floors)
    xi = int(math.floor(x)) & 255
    yi = int(math.floor(y)) & 255

    # Distances fractionnaires à l’intérieur de la cellule
    xf = x - math.floor(x)
    yf = y - math.floor(y)

    # On récupère les hash aux coins
    top_right    = PERM[PERM[xi + 1] + yi + 1]
    top_left     = PERM[PERM[xi]     + yi + 1]
    bottom_right = PERM[PERM[xi + 1] + yi]
    bottom_left  = PERM[PERM[xi]     + yi]

    # On applique la courbe de lissage fade aux coordonnées
    u = fade(xf)
    v = fade(yf)

    # On calcule les 4 gradients
    val_bottom_left  = grad(bottom_left,  xf,    yf)
    val_bottom_right = grad(bottom_right, xf-1,  yf)
    val_top_left     = grad(top_left,     xf,    yf-1)
    val_top_right    = grad(top_right,    xf-1,  yf-1)

    # On interpole horizontalement, puis verticalement
    lerp_bottom = lerp(val_bottom_left,  val_bottom_right, u)
    lerp_top    = lerp(val_top_left,     val_top_right,    u)
    return lerp(lerp_bottom, lerp_top, v)

def fractal_perlin2d(x, y, octaves=1, persistence=0.5):
    """
    Bruit de Perlin fractal : on somme plusieurs octaves
    pour obtenir un terrain plus riche.
    """
    total = 0.0
    frequency = 1.0
    amplitude = 1.0
    max_value = 0.0  # pour normaliser en [-1,1]

    for _ in range(octaves):
        total += perlin2d(x * frequency, y * frequency) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= 2.0

    # Normalisation dans l’intervalle [-1, 1]
    return total / max_value

# ------------------------------------------------------------------
#   2) Classes principales (Joueur, Balle, Ennemi, Terrain, etc.)
# ------------------------------------------------------------------

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = PLAYER_SPEED
        self.shield_active = False
        self.shield_timer = 0
        self.reload_timer = 0  # Gère l’intervalle entre deux tirs

    def update(self):
        # Déplacement (ZQSD)
        if pyxel.btn(pyxel.KEY_Z):
            self.y -= self.speed
        if pyxel.btn(pyxel.KEY_S):
            self.y += self.speed
        if pyxel.btn(pyxel.KEY_Q):
            self.x -= self.speed
        if pyxel.btn(pyxel.KEY_D):
            self.x += self.speed

        # Gestion des limites (on peut aussi gérer ça via les obstacles du terrain)
        self.x = max(0, min(self.x, MAP_WIDTH*TILE_SIZE - 1))
        self.y = max(0, min(self.y, MAP_HEIGHT*TILE_SIZE - 1))

        # Gestion du bouclier
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.activate_shield()

        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_timer = 0

        # Gestion du délai de tir
        if self.reload_timer > 0:
            self.reload_timer -= 1

    def activate_shield(self):
        self.shield_active = True
        self.shield_timer = SHIELD_DURATION

    def can_shoot(self):
        return self.reload_timer == 0

    def shoot(self):
        self.reload_timer = RELOAD_TIME


class Bullet:
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.active = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        # Désactive la balle si elle sort de la carte
        if (self.x < 0 or self.x > MAP_WIDTH*TILE_SIZE or
            self.y < 0 or self.y > MAP_HEIGHT*TILE_SIZE):
            self.active = False


class Enemy:
    def __init__(self, x, y, etype):
        self.x = x
        self.y = y
        self.etype = etype
        self.speed = 0.5 if etype == ENEMY_TYPE_CHASER else 0.3
        self.hp = 2
        self.reload_timer = 60  # pour tirer (si shooter) ou exploser (si bomber)

    def update(self, player, bullets, enemies):
        if self.etype == ENEMY_TYPE_CHASER:
            # Se diriger vers le joueur
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist != 0:
                self.x += (dx/dist) * self.speed
                self.y += (dy/dist) * self.speed

        elif self.etype == ENEMY_TYPE_SHOOTER:
            # Se déplace un peu aléatoirement et tire
            dx = player.x - self.x
            dy = player.y - self.y
            self.x += (random.random() - 0.5) * 0.5
            self.y += (random.random() - 0.5) * 0.5

            # Tir ennemi
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.reload_timer = 60
                angle = math.atan2(dy, dx)
                vx = math.cos(angle) * 2
                vy = math.sin(angle) * 2
                bullets.append(Bullet(self.x, self.y, vx, vy))

        elif self.etype == ENEMY_TYPE_BOMBER:
            # Se dirige vers le joueur et explose quand assez proche
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist != 0:
                self.x += (dx/dist) * self.speed
                self.y += (dy/dist) * self.speed

            self.reload_timer -= 1
            if dist < 8 or self.reload_timer <= 0:
                # Explosion
                # (On pourrait infliger des dégâts au joueur, etc.)
                if dist < 16 and not player.shield_active:
                    pass
                self.hp = 0  # l’ennemi se détruit

    def is_alive(self):
        return self.hp > 0


class Terrain:
    """
    Gère la génération et l’affichage du terrain via un Perlin Noise
    fait « maison ». On stocke un tableau 2D dont chaque cellule
    contient un type de tuile (0 pour « herbe », 1 pour « obstacle », etc.).
    """
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.map_data = [[0 for _ in range(width)] for _ in range(height)]
        self.generate()

    def generate(self):
        scale = 0.05
        octaves = 2
        for y in range(self.height):
            for x in range(self.width):
                # On appelle notre fractal_perlin2d fait maison
                noise_val = fractal_perlin2d(x*scale, y*scale, octaves=octaves, persistence=0.5)
                # noise_val ∈ [-1, 1]
                if noise_val < -0.1:
                    self.map_data[y][x] = 1  # obstacle
                else:
                    self.map_data[y][x] = 0  # terrain normal

    def is_obstacle(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        return self.map_data[y][x] == 1

    def draw(self, cam_x, cam_y):
        # Dessiner la portion visible du terrain
        start_x = int(cam_x // TILE_SIZE)
        start_y = int(cam_y // TILE_SIZE)
        end_x = start_x + (WINDOW_WIDTH // TILE_SIZE) + 2
        end_y = start_y + (WINDOW_HEIGHT // TILE_SIZE) + 2

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    tile = self.map_data[ty][tx]
                    px = tx * TILE_SIZE - cam_x
                    py = ty * TILE_SIZE - cam_y
                    if tile == 0:
                        # herbe
                        pyxel.rect(px, py, TILE_SIZE, TILE_SIZE, 3)
                    else:
                        # obstacle
                        pyxel.rect(px, py, TILE_SIZE, TILE_SIZE, 11)


# ------------------------------------------------------------------
#   3) Classe principale du jeu
# ------------------------------------------------------------------

class Game:
    def __init__(self):
        pyxel.init(WINDOW_WIDTH, WINDOW_HEIGHT, fps=60)
        pyxel.title = "Zelda-like au pistolet"

        pyxel.mouse(True)

        # Créer le terrain, le joueur, etc.
        self.terrain = Terrain(MAP_WIDTH, MAP_HEIGHT)
        self.player = Player(MAP_WIDTH*TILE_SIZE//2, MAP_HEIGHT*TILE_SIZE//2)

        # Liste de balles (tirées par le joueur ou les ennemis)
        self.bullets = []

        # Liste d’ennemis - on en place quelques-uns aléatoirement
        self.enemies = []
        for _ in range(10):
            x = random.randint(0, MAP_WIDTH*TILE_SIZE)
            y = random.randint(0, MAP_HEIGHT*TILE_SIZE)
            etype = random.choice([ENEMY_TYPE_CHASER, ENEMY_TYPE_SHOOTER, ENEMY_TYPE_BOMBER])
            self.enemies.append(Enemy(x, y, etype))

        pyxel.run(self.update, self.draw)

    def update(self):
        # Mise à jour du joueur
        self.player.update()

        # Tir du joueur (clic gauche)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.player.can_shoot():
            # Calcul de la direction du tir (vers la souris)
            mouse_x = pyxel.mouse_x + self.camera_x
            mouse_y = pyxel.mouse_y + self.camera_y
            dx = mouse_x - self.player.x
            dy = mouse_y - self.player.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist != 0:
                vx = (dx / dist) * BULLET_SPEED
                vy = (dy / dist) * BULLET_SPEED
                self.bullets.append(Bullet(self.player.x, self.player.y, vx, vy))
            self.player.shoot()

        # Mise à jour des balles
        for bullet in self.bullets:
            bullet.update()

        # Mise à jour des ennemis
        for enemy in self.enemies:
            enemy.update(self.player, self.bullets, self.enemies)

        # Vérification des collisions balles <-> ennemis
        for bullet in self.bullets:
            if bullet.active:
                for enemy in self.enemies:
                    if enemy.is_alive():
                        # collision simple par distance
                        if (enemy.x - bullet.x)**2 + (enemy.y - bullet.y)**2 < (4**2):
                            bullet.active = False
                            enemy.hp -= 1
                            break

        # Nettoyage des balles inactives
        self.bullets = [b for b in self.bullets if b.active]
        # Nettoyage des ennemis morts
        self.enemies = [e for e in self.enemies if e.is_alive()]

    @property
    def camera_x(self):
        # Caméra centrée sur le joueur
        half_w = WINDOW_WIDTH / 2
        cam_x = self.player.x - half_w
        # Limiter la caméra pour qu’elle ne sorte pas du terrain
        cam_x = max(0, min(cam_x, MAP_WIDTH*TILE_SIZE - WINDOW_WIDTH))
        return cam_x

    @property
    def camera_y(self):
        half_h = WINDOW_HEIGHT / 2
        cam_y = self.player.y - half_h
        cam_y = max(0, min(cam_y, MAP_HEIGHT*TILE_SIZE - WINDOW_HEIGHT))
        return cam_y

    def draw(self):
        pyxel.cls(0)

        self.terrain.draw(self.camera_x, self.camera_y)

        px = self.player.x - self.camera_x
        py = self.player.y - self.camera_y
        color_player = 9 if not self.player.shield_active else 10
        pyxel.rect(px-3, py-3, 6, 6, color_player)

        for bullet in self.bullets:
            bx = bullet.x - self.camera_x
            by = bullet.y - self.camera_y
            pyxel.rect(bx-1, by-1, 2, 2, 7)

        for enemy in self.enemies:
            ex = enemy.x - self.camera_x
            ey = enemy.y - self.camera_y
            if enemy.etype == ENEMY_TYPE_CHASER:
                pyxel.circ(ex, ey, 3, 8)  # vert
            elif enemy.etype == ENEMY_TYPE_SHOOTER:
                pyxel.circ(ex, ey, 3, 2)  # rouge
            elif enemy.etype == ENEMY_TYPE_BOMBER:
                pyxel.circ(ex, ey, 3, 10) # jaune

        # Indications à l’écran
        pyxel.text(5, 5, "Clic gauche: Tir | Clic droit: Bouclier", 7)
        pyxel.text(5, 15, f"Ennemis: {len(self.enemies)}", 7)

# ------------------------------------------------------------------
#   4) Lancement du jeu
# ------------------------------------------------------------------

if __name__ == "__main__":
    Game()
