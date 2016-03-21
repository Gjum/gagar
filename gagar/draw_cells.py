from time import time

from agarnet.vec import Vec
from .subscriber import Subscriber
from .drawutils import *

info_size = 14


def nick_size(cell, w):
    return max(14, w.world_to_screen_size(.3 * cell.size))


class CellsDrawer(Subscriber):
    def on_draw_cells(self, c, w):
        # reverse to show small over large cells
        for cell in sorted(w.world.cells.values(), reverse=True):
            pos = w.world_to_screen_pos(cell.pos)
            c.fill_circle(pos, w.world_to_screen_size(cell.size),
                          color=to_rgba(cell.color, .8))


class CellNames(Subscriber):
    def on_draw_cells(self, c, w):
        for cell in w.world.cells.values():
            if cell.name:
                pos = w.world_to_screen_pos(cell.pos)
                size = nick_size(cell, w)
                c.draw_text(pos, '%s' % cell.name,
                            align='center', outline=(BLACK, 2), size=size)


class RemergeTimes(Subscriber):
    def __init__(self, client):
        self.client = client
        self.split_times = {}

    def on_own_id(self, cid):
        self.split_times[cid] = time()

    def on_draw_cells(self, c, w):
        player = self.client.player
        if len(player.own_ids) <= 1:
            return  # dead or only one cell, no remerge time to display
        now = time()
        for cell in player.own_cells:
            if cell.cid not in self.split_times: continue
            split_for = now - self.split_times[cell.cid]
            # formula by HungryBlob
            ttr = max(30, cell.size // 5) - split_for
            if ttr < 0: continue
            pos = w.world_to_screen_pos(cell.pos)
            pos.isub(Vec(0, (info_size + nick_size(cell, w)) / 2))
            c.draw_text(pos, 'TTR %.1fs' % ttr,
                        align='center', outline=(BLACK, 2), size=info_size)


class CellMasses(Subscriber):
    def on_draw_cells(self, c, w):
        for cell in w.world.cells.values():
            if cell.is_food or cell.is_ejected_mass or cell.mass < 5:
                continue
            pos = w.world_to_screen_pos(cell.pos)
            if cell.name:
                pos.iadd(Vec(0, (info_size + nick_size(cell, w)) / 2))
            c.draw_text(pos, '%i' % cell.mass,
                        align='center', outline=(BLACK, 2), size=info_size)


class CellHostility(Subscriber):
    def on_draw_cells(self, c, w):
        if not w.player.is_alive: return  # nothing to be hostile against
        own_min_mass = min(c.mass for c in w.player.own_cells)
        own_max_mass = max(c.mass for c in w.player.own_cells)
        for cell in w.world.cells.values():
            if cell.is_food or cell.is_ejected_mass:
                continue  # no threat
            if cell.cid in w.player.own_ids:
                continue  # own cell, also no threat lol
            pos = w.world_to_screen_pos(cell.pos)
            color = YELLOW
            if cell.is_virus:
                if own_max_mass > cell.mass:
                    color = RED
                else:
                    continue  # no threat, do not mark
            elif own_min_mass > cell.mass * 1.33 * 2:
                color = PURPLE
            elif own_min_mass > cell.mass * 1.33:
                color = GREEN
            elif cell.mass > own_min_mass * 1.33 * 2:
                color = RED
            elif cell.mass > own_min_mass * 1.33:
                color = ORANGE
            c.stroke_circle(pos, w.world_to_screen_size(cell.size),
                            width=5, color=color)


class ForceFields(Subscriber):
    def on_draw_cells(self, c, w):
        split_dist = 760
        for cell in w.player.own_cells:
            pos = w.world_to_screen_pos(cell.pos)
            radius = split_dist + cell.size * .7071
            c.stroke_circle(pos, w.world_to_screen_size(radius),
                            width=3, color=to_rgba(PURPLE, .5))

        if w.player.is_alive:
            own_max_size = max(c.size for c in w.player.own_cells)
            own_min_mass = min(c.mass for c in w.player.own_cells)
        else:  # spectating or dead, still draw some lines
            own_max_size = own_min_mass = 0

        for cell in w.world.cells.values():
            if cell.size < 60:
                continue  # cannot split
            if cell.cid in w.player.own_ids:
                continue  # own cell, not hostile
            pos = w.world_to_screen_pos(cell.pos)
            if cell.is_virus:
                if own_max_size > cell.size:  # dangerous virus
                    c.stroke_circle(pos, w.world_to_screen_size(own_max_size),
                                    width=3, color=to_rgba(RED, .5))
            elif cell.mass > own_min_mass * 1.33 * 2:  # can split+kill me
                radius = max(split_dist + cell.size * .7071, cell.size)
                c.stroke_circle(pos, w.world_to_screen_size(radius),
                                width=3, color=to_rgba(RED, .5))


class MovementLines(Subscriber):
    def on_draw_cells(self, c, w):
        for cell in w.player.own_cells:
            c.draw_line(w.world_to_screen_pos(cell.pos), w.mouse_pos,
                        width=1, color=to_rgba(BLACK, .3))
