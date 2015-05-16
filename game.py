import pygame
from pygame.locals import *

pygame.init()
pygame.font.init()

WHITE = (255,255,255)
DARKGREY = (50,50,50)
BLUE = (50,50,255)

BG_COLOR = DARKGREY

FONT = pygame.font.Font(None, 20)

def draw_text(screen, text, centerpos, color=WHITE):
    img = FONT.render(text, 1, color)
    textpos = img.get_rect(center=centerpos)
    screen.blit(img, textpos)

class Cell:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 0  # radius
        self.name = ''
        self.color = BLUE
        self.virus = False

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, pos_or_x, y=None):
        if y: pos_or_x = (pos_or_x, y)
        self.x, self.y = pos_or_x

    def draw(self, screen):
        center = (self.x, self.y)
        pygame.draw.circle(screen, self.color, center, self.size)
        if self.name: draw_text(screen, self.name, center)

screen = pygame.display.set_mode((600,600))

c = Cell()
c.x, c.y, c.size = 60, 40, 20
c.name = 'sdfsdf'

cells = [c]*100

def draw_all():
    screen.fill(BG_COLOR)
    for c in cells:
        c.draw(screen)
    pygame.display.flip()

while pygame.event.poll().type != KEYDOWN:
    mouse_pos = pygame.mouse.get_pos()
    c.pos = mouse_pos

    draw_all()

    pygame.time.delay(10)
