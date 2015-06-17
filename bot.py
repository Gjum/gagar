import random
from client import special_names
from event import Subscriber
from vec import Vec

# TODO highlight eatable, can_eat, ...
# TODO weighted distraction from can_eat

def nearest_from(pos, cells):
    return sorted(((pos - c.pos).lensq(), c) for c in cells)

class CellInfo:
    def __init__(self, cell):
        self.cell = cell
        self.old_pos = self.cell.pos.copy()
        self.old_size = self.cell.size

    def save_old(self):
        self.old_pos = self.cell.pos.copy()
        self.old_size = self.cell.size

    @property
    def direction(self):
        return self.cell.pos - self.old_pos

class Bot(Subscriber):

    def __init__(self, channel, client):
        super().__init__(channel)
        self.client = client
        self.target = Vec()
        self.paths = []
        self.cell_info = {}

    def on_ingame(self):
        self.client.player.name = random.choice(special_names)
        self.client.send_respawn()

    def on_death(self):
        self.client.player.name = random.choice(special_names)
        self.client.send_respawn()

    def on_cell_info(self, cid, **_):
        if cid not in self.cell_info:
            self.cell_info[cid] = CellInfo(self.client.world.cells[cid])
        self.cell_info[cid].save_old()

    def on_cell_removed(self, cid):
        if cid in self.cell_info:
            del self.cell_info[cid]

    def on_draw(self, c, w):
        if not w.show_debug:
            return

        # highlight target
        c.set_source_rgba(1,1,1, .8)
        x, y = w.world_to_screen_pos(self.target)
        c.arc(x, y, 7*w.screen_scale, 0, 6.28)
        c.fill()

        # line to target
        c.set_source_rgba(1,1,1, .8)
        for cid in self.client.player.own_ids:
            c.move_to(x, y)
            c.line_to(*w.world_to_screen_pos(self.client.world.cells[cid].pos))
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

    def on_world_update_post(self):
        player = self.client.player

        if not player.is_alive:
            return  # dead, wait for respawn

        min_size = min(cell.size for cell in player.own_cells)
        max_size = max(cell.size for cell in player.own_cells)

        friendly_viruses = []
        deadly_viruses = []
        food = []
        splitkill_eatable = []
        eatable = []
        can_eat = []
        can_splitkill = []
        for cell in self.client.world.cells.values():
            if cell.cid  in player.own_ids:
                continue
            if cell.is_virus:
                if cell.size >= max_size:
                    friendly_viruses.append(cell)
                else:
                    deadly_viruses.append(cell)
                continue
            if cell.size < 37:
                food.append(cell)
            if cell.size < .9 * .5 * min_size:  # xxx .5?
                splitkill_eatable.append(cell)
            if cell.size < .9 * min_size:
                eatable.append(cell)
            if cell.size * .9 > min_size:
                can_eat.append(cell)
            if cell.size * .9 * .5 > min_size:
                can_splitkill.append(cell)

        # we can eat the cells in eatable,
        #    maybe in deadly_viruses (if >= 16 cells)
        # we shoud avoid all cells in can_eat and deadly_viruses,
        #    maybe in can_splitkill

        if not eatable:
            return  # TODO find any target

        depth = 3
        breadth = 4

        paths = [(0, [cell]) for cell in player.own_cells]
        for i in range(min(len(eatable), depth)):
            new_paths = []
            for dist, p_cells in paths:
                last_pos = p_cells[-1].pos
                for add_dist, c_next in nearest_from(last_pos, eatable)[:breadth]:
                    if c_next not in p_cells:
                        new_paths.append((dist + add_dist, p_cells + [c_next]))
            paths = new_paths
        self.paths = paths

        try:
            self.target = paths[0][1][1].pos
            self.client.send_mouse(*self.target)
        except IndexError:
            pass
