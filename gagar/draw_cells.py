from time import time

from agario.vec import Vec
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
            draw_circle(c, pos, w.world_to_screen_size(cell.size),
                        color=to_rgba(cell.color, .8))


class CellNames(Subscriber):
    def on_draw_cells(self, c, w):
        for cell in w.world.cells.values():
            if cell.name:
                pos = w.world_to_screen_pos(cell.pos)
                size = nick_size(cell, w)
                draw_text(c, pos, '%s' % cell.name,
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
            split_for = now - self.split_times[cell.cid]
            # formula by DebugMonkey
            ttr = (player.total_mass * 20 + 30000) / 1000 - split_for
            if ttr < 0: continue
            pos = w.world_to_screen_pos(cell.pos)
            pos.isub(Vec(0, (info_size + nick_size(cell, w)) / 2))
            draw_text(c, pos, 'TTR %.1fs after %.1fs' % (ttr, split_for),
                      align='center', outline=(BLACK, 2), size=info_size)


class CellMasses(Subscriber):
    def on_draw_cells(self, c, w):
        for cell in w.world.cells.values():
            if cell.is_food or cell.is_ejected_mass:
                continue
            pos = w.world_to_screen_pos(cell.pos)
            if cell.name:
                pos.iadd(Vec(0, (info_size + nick_size(cell, w)) / 2))
            draw_text(c, pos, '%i' % cell.mass,
                      align='center', outline=(BLACK, 2), size=info_size)


class CellHostility(Subscriber):
    def on_draw_cells(self, c, w):
        if not w.player.is_alive: return  # nothing to be hostile against
        own_min_mass = min(c.mass for c in w.player.own_cells)
        own_max_mass = max(c.mass for c in w.player.own_cells)
        lw = c.get_line_width()
        c.set_line_width(5)
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
            elif own_min_mass > cell.mass * 1.25 * 2:
                color = PURPLE
            elif own_min_mass > cell.mass * 1.25:
                color = GREEN
            elif cell.mass > own_min_mass * 1.25 * 2:
                color = RED
            elif cell.mass > own_min_mass * 1.25:
                color = ORANGE
            c.set_source_rgba(*color)
            draw_circle_outline(c, pos, w.world_to_screen_size(cell.size))
        c.set_line_width(lw)


class ForceFields(Subscriber):
    def on_draw_cells(self, c, w):
        if not w.player.is_alive: return  # nothing to be hostile against
        split_dist = 760
        c.set_line_width(3)
        c.set_source_rgba(*to_rgba(PURPLE, .5))
        for cell in w.player.own_cells:
            pos = w.world_to_screen_pos(cell.pos)
            radius = split_dist + cell.size / 2
            draw_circle_outline(c, pos, w.world_to_screen_size(radius))

        own_max_size = max(c.size for c in w.player.own_cells)
        own_min_mass = min(c.mass for c in w.player.own_cells)
        c.set_source_rgba(*to_rgba(RED, .5))
        for cell in w.world.cells.values():
            if cell.is_food or cell.is_ejected_mass:
                continue
            if cell.cid in w.player.own_ids:
                continue
            pos = w.world_to_screen_pos(cell.pos)
            if cell.is_virus:
                if own_max_size > cell.size:  # dangerous virus
                    draw_circle_outline(c, pos, w.world_to_screen_size(own_max_size))
            elif cell.mass > own_min_mass * 1.25 * 2:  # can split+kill me
                radius = split_dist + cell.size / 2
                draw_circle_outline(c, pos, w.world_to_screen_size(radius))


class MovementLines(Subscriber):
    def on_draw_cells(self, c, w):
        c.set_line_width(1)
        c.set_source_rgba(*to_rgba(BLACK, .3))
        for cell in w.player.own_cells:
            c.move_to(*w.world_to_screen_pos(cell.pos))
            c.line_to(*w.mouse_pos)
            c.stroke()
