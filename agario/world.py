"""
Copyright (C) 2015  Gjum

code.gjum@gmail.com

This file is part of pyagario.

pyagario is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyagario is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pyagario.  If not, see <http://www.gnu.org/licenses/>.
"""

from collections import defaultdict
from .vec import Vec


class Cell(object):
    def __init__(self, cid=-1, x=0, y=0, size=0, name='',
                 color=(1, 0, 1), is_virus=False, is_agitated=False):
        self.cid = cid
        self.pos = Vec(x, y)
        self.size = size
        self.mass = size**2 / 100.0
        self.name = getattr(self, 'name', name) or name
        self.color = tuple(map(lambda rgb: rgb / 255.0, color))
        self.is_virus = is_virus
        self.is_agitated = is_agitated

    @property
    def is_food(self):
        return self.size < 20 and not self.name

    @property
    def is_ejected_mass(self):
        return self.size in (37, 38) and not self.name

    def same_player(self, other):
        """
        Compares name and color.
        Returns True if both are owned by the same player.
        """
        return self.name == other.name \
                and self.color == other.color

    def __lt__(self, other):
        if self.mass != other.mass:
            return self.mass < other.mass
        return self.cid < other.cid


class World(object):
    def __init__(self):
        self.cells = defaultdict(Cell)
        self.leaderboard_names = []
        self.leaderboard_groups = []
        self.top_left = Vec(0, 0)
        self.bottom_right = Vec(0, 0)

    @property
    def center(self):
        return (self.top_left + self.bottom_right) / 2

    @property
    def size(self):
        return self.top_left.abs() + self.bottom_right.abs()

    def __eq__(self, other):
        """Compare two worlds by comparing their leaderboards."""
        for ls, lo in zip(self.leaderboard_names, other.leaderboard_names):
            if ls != lo:
                return False
        for ls, lo in zip(self.leaderboard_groups, other.leaderboard_groups):
            if ls != lo:
                return False
        if self.top_left != other.top_left:
            return False
        if self.bottom_right != other.bottom_right:
            return False
        return True


class Player(object):
    def __init__(self):
        self.world = World()
        self.own_ids = set()
        self.nick = ''
        self.scale = 1
        self.center = self.world.center
        self.total_size = 0
        self.total_mass = 0

    def cells_changed(self):
        self.total_size = sum(cell.size for cell in self.own_cells)
        self.total_mass = sum(cell.mass for cell in self.own_cells)
        self.scale = pow(min(1.0, 64.0 / self.total_size), 0.4) \
            if self.total_size > 0 else 1.0

        if self.own_ids:
            left   = min(cell.pos.x for cell in self.own_cells)
            right  = max(cell.pos.x for cell in self.own_cells)
            top    = min(cell.pos.y for cell in self.own_cells)
            bottom = max(cell.pos.y for cell in self.own_cells)
            self.center = Vec(left + right, top + bottom) / 2
        # else: keep old center

    @property
    def own_cells(self):
        cells = self.world.cells
        return (cells[cid] for cid in self.own_ids)

    @property
    def is_alive(self):
        return bool(self.own_ids)

    @property
    def is_spectating(self):
        return not self.is_alive

    # @property
    # def visible_area(self):
    #     """Calculated like in the vanilla client."""
    #     raise NotImplementedError
    #     return Vec(), Vec()
