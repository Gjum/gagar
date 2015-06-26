import copy
import random
from client import special_names
from drawing_helpers import *
from vec import Vec

# TODO highlight eatable, can_eat, ...
# TODO weighted distraction from can_eat

def nearest_from(pos, cells):
    return sorted(((pos - c.pos).lensq(), c) for c in cells)

def cell_speed(cell):
    return 30 * cell.mass ** (-1/4.5)


class Avoid:
    def __init__(self, client, key_movement_lines=ord('l')):
        self.client = client
        self.movement_delta = Vec()#100, 200)
        self.show_lines = True
        self.key_movement_lines = key_movement_lines

        self.prev_cells = {}
        self.paths = []
        self.cell_info = {}

    def on_ingame(self):
        self.client.player.nick = random.choice(special_names)
        self.client.send_respawn()

    def on_death(self):
        self.client.player.nick = random.choice(special_names)
        self.client.send_respawn()

    @property
    def mouse_world(self):
        return self.client.player.center + self.movement_delta

    def on_key_pressed(self, val, char):
        if char == 'k':
            self.client.send_explode()
        elif val == self.key_movement_lines:
            self.show_lines = not self.show_lines

    def on_draw_cells(self, c, w):
        if self.show_lines:
            mouse_pos = w.world_to_screen_pos(self.mouse_world)
            c.set_source_rgba(*to_rgba(BLACK, .3))
            for cell in self.client.player.own_cells:
                c.move_to(*w.world_to_screen_pos(cell.pos))
                c.line_to(*mouse_pos)
                c.stroke()

            for new_cell in self.client.player.world.cells.values():
                if new_cell.cid in self.client.player.own_ids:
                    continue
                if new_cell.cid not in self.prev_cells:
                    continue
                old_cell = self.prev_cells[new_cell.cid]

                c.set_source_rgba(*LIGHT_GRAY)
                delta = (new_cell.pos - old_cell.pos) * 10
                c.move_to(*w.world_to_screen_pos(new_cell.pos + delta))
                c.line_to(*w.world_to_screen_pos(new_cell.pos))
                c.stroke()

            # paths
            c.set_source_rgba(1,1,1, .2)
            drawn = []
            for _, path in self.paths[1:]:
                c_prev = None
                for cell in path:
                    c_from_to = (c_prev, cell)
                    if c_prev and c_from_to not in drawn:
                        c.move_to(*w.world_to_screen_pos(c_prev.pos))
                        c.line_to(*w.world_to_screen_pos(cell.pos))
                        c.stroke()
                        drawn.append(c_from_to)
                    c_prev = cell

            if self.paths:
                # first (active) path
                c.set_source_rgba(0,1,0, 1)
                c_prev = None
                for cell in self.paths[0][1]:
                    if c_prev:
                        c.move_to(*w.world_to_screen_pos(c_prev.pos))
                        c.line_to(*w.world_to_screen_pos(cell.pos))
                        c.stroke()
                    c_prev = cell

    def get_prev_cell(self, new_cell):
        if new_cell.cid in self.prev_cells:
            return self.prev_cells[new_cell.cid]
        else: return new_cell

    def on_world_update_pre(self):
        self.prev_cells = copy.deepcopy(self.client.player.world.cells)

    def collect_tick_data(self):
        class Data:
            def __getattr__(self, item):
                return None
        d = Data()
        p = self.client.player

        d.min_mass = min(cell.mass for cell in p.own_cells)
        d.max_mass = max(cell.mass for cell in p.own_cells)

        # categorize cells based on size
        d.friendly_viruses = []
        d.deadly_viruses = []
        d.food = []
        d.splitkillable = []
        d.eatable = []
        d.hostile = []
        d.dangerous = []
        for cell in self.client.world.cells.values():
            if cell.cid in p.own_ids:
                pass
            elif cell.is_virus:
                if cell.mass >= d.max_mass:
                    d.friendly_viruses.append(cell)
                else:
                    d.deadly_viruses.append(cell)
            elif cell.is_food:
                d.food.append(cell)
            elif d.min_mass > cell.mass * 1.25 * 2:
                d.splitkillable.append(cell)
            elif d.min_mass > cell.mass * 1.25:
                d.eatable.append(cell)
            elif cell.mass > d.min_mass * 1.25:
                d.dangerous.append(cell)
            elif cell.mass > d.min_mass * 1.25 * 2:
                d.hostile.append(cell)

        return d

    def on_world_update_post(self):
        p = self.client.player

        if not p.is_alive:
            return  # dead, wait for respawn

        d = self.collect_tick_data()

        # we can eat the cells in eatable,
        #    maybe in deadly_viruses (if >= 16 cells)
        # we should avoid all cells in can_eat and deadly_viruses,
        #    maybe in can_splitkill

        if d.hostile or d.dangerous:
            md = Vec()
            own_cell, *_ = p.own_cells
            for cell in d.hostile + d.dangerous:
                speed = cell_speed(cell)
                dist = (own_cell.pos - cell.pos).len()
                if 3*speed < dist - cell.size:
                    continue  # too far away
                try:
                    delta = (own_cell.pos - cell.pos).set_len(speed)
                    md += delta
                except ZeroDivisionError:
                    pass

            if md:
                print('fleeing')
                self.movement_delta = md * own_cell.size
                self.client.send_mouse(*self.mouse_world)
                return

        if not d.food:
            print('no path')
            return  # TODO find any target

        print('eating food')

        depth = 3
        breadth = 4

        paths = [(0, [cell]) for cell in p.own_cells]
        for i in range(min(len(d.food), depth)):
            new_paths = []
            for dist, p_cells in paths:
                last_pos = p_cells[-1].pos
                for add_dist, c_next in nearest_from(last_pos, d.food)[:breadth]:
                    if c_next not in p_cells:
                        new_paths.append((dist + add_dist, p_cells + [c_next]))
            paths = new_paths
        self.paths = paths

        try:
            self.client.send_mouse(*paths[0][1][1].pos)
        except IndexError:
            print('err lol')

