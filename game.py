from collections import defaultdict
import pygame
from pygame.locals import *
from client import AgarClient

pygame.init()
pygame.font.init()

WHITE = (255,255,255)
DARKGREY = (50,50,50)
BLUE = (50,50,255)
FUCHSIA = (255,0,255)

BG_COLOR = DARKGREY

FONT = pygame.font.Font(None, 20)

def draw_text(screen, text, centerpos, color=WHITE):
    img = FONT.render(text, 1, color)
    textpos = img.get_rect(center=centerpos)
    screen.blit(img, textpos)

# noinspection PyAttributeOutsideInit
class Cell:
    def __init__(self):
        self.update()

    def update(self, cid=-1, x=-1, y=-1, size=10, name='ERR',
               color=FUCHSIA, is_virus=False, is_agitated=False):
        self.cid = cid
        self.x = x
        self.y = y
        self.size = size
        self.name = name
        self.color = color
        self.is_virus = is_virus
        self.is_agitated = is_agitated

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, pos_or_x, y=None):
        if y: pos_or_x = (pos_or_x, y)
        self.x, self.y = pos_or_x

    def draw(self, screen, scale, offset):
        center = tuple(map(lambda p, o: int(scale * (p - o)),
                           self.pos, offset))
        pygame.draw.circle(screen, self.color, center, int(self.size))
        if self.name: draw_text(screen, self.name, center)

# noinspection PyAttributeOutsideInit
class AgarGame(AgarClient):
    RENDER = USEREVENT + 1

    def __init__(self):
        AgarClient.__init__(self)
        self.add_handler('open', lambda **data: self.send_handshake())
        self.add_handler('leaderboard_names', self.leaderboard_names)
        self.add_handler('cell_eaten', self.cell_eaten)
        self.add_handler('cell_info', self.cell_info)
        self.add_handler('cell_keep', self.cell_keep)

        self.screen = pygame.display.set_mode((700,700))
        self.reset_game()
        pygame.time.set_timer(self.RENDER, 100)

    def reset_game(self):
        self.own_id = -1
        self.cells = defaultdict(Cell)

    def leaderboard_names(self, leaderboard):
        pass  # TODO

    def cell_eaten(self, a, b):
        pass  # TODO

    def cell_info(self, **kwargs):
        self.cells[kwargs['cid']].update(**kwargs)

    def cell_keep(self, keep_cells):
        # for cid in list(self.cells)[:]:
        #     if cid not in keep_cells:
        #         del self.cells[cid]

        # called every tick
        self.input()

    def input(self):
        while 1:
            event = pygame.event.poll()
            if event.type == 0:
                break
            elif event.type == KEYDOWN:
                pygame.quit()
                self.disconnect()
                print('Stopped')
                return
            elif event.type == self.RENDER:
                self.render()

    def render(self):
        scale = self.screen.get_rect().height / 11500.0
        offset = 0, 0

        self.screen.fill(BG_COLOR)
        for c in self.cells.values():
            c.draw(self.screen, scale, offset)
        pygame.display.flip()

game = AgarGame()
game.crash_on_errors = True

url = 'ws://213.168.249.220:443'
try:
    game.connect(url)
except KeyboardInterrupt:
    print('KeyboardInterrupt')
print('Done')
