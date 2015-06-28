import copy
import random
import time
from client import special_names
from drawing_helpers import *
from vec import Vec


def cell_speed(cell):
    return 30 * cell.mass ** (-1/4.5)


class Avoid:
    def __init__(self, client, key_movement_lines=ord('l')):
        self.client = client
        self.key_movement_lines = key_movement_lines
        self.show_lines = True

        self.respawn_timeout = 0  # ticks to wait before sending next respawn
        self.prev_cells = {}
        self.target_pos = Vec()
        self.flee_intolerance = 5  # ticks to look ahead for cell collision
        self.paths = []
        self.keep_paths_step = 50

    def respawn(self):
        if self.respawn_timeout > 0:
            return  # wait until it is decreased in on_world_update_post()
        self.respawn_timeout = 25  # xxx could be anything really
        self.client.player.nick = random.choice(special_names)
        self.client.send_respawn()

    def on_ingame(self):
        self.respawn()

    def on_death(self):
        self.respawn()

    def on_key_pressed(self, val, char):
        if char == 'k':
            self.client.send_explode()
        elif val == self.key_movement_lines:
            self.show_lines = not self.show_lines

    def on_draw_cells(self, c, w):
        if self.show_lines:
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

            if self.flee_intolerance > 5:
                # fleeing circles
                for cell in self.data.hostile + self.data.dangerous:
                    speed = cell_speed(cell)
                    radius = self.flee_intolerance * speed + cell.size
                    draw_circle_outline(c, w.world_to_screen_pos(cell.pos),
                                        radius * w.screen_scale, (1,0,0))
            elif self.paths:
                # paths
                # draw first (actively followed) path in green
                c.set_source_rgba(0,1,0, 1)
                drawn_edges = []
                for _, path in self.paths:
                    prev_pos = self.client.player.center
                    for cell in path:
                        edge_from_to = (prev_pos, cell.pos)
                        if edge_from_to not in drawn_edges:
                            drawn_edges.append(edge_from_to)
                            c.move_to(*w.world_to_screen_pos(prev_pos))
                            c.line_to(*w.world_to_screen_pos(cell.pos))
                            c.stroke()
                        prev_pos = cell.pos
                    # draw all in gray except first path
                    c.set_source_rgba(1,1,1, .2)

            # highlight target and movement directions
            mouse_pos = w.world_to_screen_pos(self.target_pos)
            c.set_source_rgba(*to_rgba(BLACK, .3))
            for cell in self.client.player.own_cells:
                c.move_to(*w.world_to_screen_pos(cell.pos))
                c.line_to(*mouse_pos)
                c.stroke()
            draw_circle(c, mouse_pos, 5, WHITE)

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

        self.data = d
        return d

    def on_world_update_post(self):
        if True or self.respawn_timeout > 0: self.respawn_timeout -= 1

        p = self.client.player

        if not p.is_alive:
            self.respawn()
            self.client.subscriber.on_update_msg('dead, respawning...', 1)
            return

        d = self.collect_tick_data()

        # we can eat the cells in eatable,
        #    maybe in deadly_viruses (if >= 16 cells)
        # we should avoid all cells in can_eat and deadly_viruses,
        #    maybe in can_splitkill

        num_fleeing = 0
        md = Vec()
        own_cell, *_ = p.own_cells
        if d.hostile or d.dangerous:  # check if fleeing necessary
            for cell in d.hostile + d.dangerous:
                speed = cell_speed(cell)
                dist = (own_cell.pos - cell.pos).len()
                if self.flee_intolerance * speed < dist - cell.size:
                    continue  # too far away
                try:
                    md += (own_cell.pos - cell.pos).set_len(speed)
                    num_fleeing += 1
                    # increase intolerance if necessary
                    self.flee_intolerance = max(10 * num_fleeing, self.flee_intolerance)
                except ZeroDivisionError:
                    pass

        if num_fleeing > 0:
            self.target_pos = own_cell.pos + md * own_cell.size
            self.client.subscriber.on_update_msg('fleeing from %i' % num_fleeing, 1)
        else:  # not fleeing
            self.flee_intolerance = 5
            self.calc_food_target(d)

        self.client.send_target(*self.target_pos)

    def calc_food_target(self, d):
        if not d.food:
            self.client.subscriber.on_update_msg('no food to go after', 1)
            return

        # fast sorting because only the first few (num) are needed
        def nearest_from(pos, cells, num, skip=[]):
            nearest = []
            for c in cells:
                if c in skip: continue
                cd = (pos - c.pos).lensq()
                if len(nearest) < num:
                    nearest.append((cd, c))
                    # print(' '.join('%i' % d for d, c in nearest))
                    nearest.sort()
                else:
                    nd, n = nearest[-1]
                    if cd < nd:
                        nearest[-1] = (cd, c)
                        nearest.sort()
                        # print(' '.join('%i' % d for d, c in nearest))
            return nearest

        p = self.client.player

        start_time = time.time()
        breadth = 10
        paths = [(0, [cell]) for cell in p.own_cells]
        outatime = False
        for depth in range(len(d.food)):
            new_paths = []
            for dist, p_cells in paths:
                last_pos = p_cells[-1].pos
                for add_dist, c_next in nearest_from(last_pos, d.food, breadth, p_cells):
                    new_paths.append((dist + add_dist, p_cells + [c_next]))
                    outatime = start_time + .5/25. < time.time()
                    if outatime: break
                if outatime: break
            if outatime: break
            if not new_paths:
                break
            paths = new_paths[:self.keep_paths_step]
        self.paths = paths

        if depth > 5:
            self.keep_paths_step += 10
        else:
            self.keep_paths_step = max(10, int(.5 * self.keep_paths_step))

        try:
            self.target_pos = self.paths[0][1][1].pos
            self.client.subscriber.on_update_msg('eating food, depth: %i, keep: %i' % (depth, self.keep_paths_step), 1)
        except IndexError:
            self.client.subscriber.on_update_msg('no path found', 1)
