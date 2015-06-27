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

from gi.repository import Gtk, Gdk

from drawing_helpers import *
from vec import Vec


class WorldViewer:
    """
    Draws one world and handles keys/mouse.
    Does not poll for events itself.
    Calls input_subscriber.on_{key_pressed|mouse_moved}() methods on key/mouse input.
    Calls draw_subscriber.on_draw_{background|cells|hud}() methods when drawing.
    """

    INFO_SIZE = 300

    def __init__(self, world):
        self.world = world
        self.client = None  # the focused player, or None to show full world

        # the class instance on which to call on_key_pressed and on_mouse_moved
        self.input_subscriber = None
        # same for draw_background, draw_cells, draw_hud
        self.draw_subscriber = None

        self.win_size = Vec(1000, 1000 * 9 / 16)
        self.screen_center = self.win_size / 2
        self.screen_scale = 1
        self.world_center = Vec(0, 0)

        window = Gtk.Window()
        window.set_title('agar.io')
        window.set_default_size(self.win_size.x, self.win_size.y)
        window.connect('delete-event', Gtk.main_quit)

        self.drawing_area = Gtk.DrawingArea()
        window.add(self.drawing_area)

        window.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
        window.connect('key-press-event', self.key_pressed)
        window.connect('motion-notify-event', self.mouse_moved)
        self.drawing_area.connect('draw', self.draw)

        window.show_all()

    def focus_client(self, client):
        """Follow this client regarding center and zoom."""
        self.client = client
        self.world = client.world

    def show_full_world(self, world=None):
        """
        Show the full world view instead of one client.
        :param world: optionally update the drawn world
        """
        self.client = None
        if world:
            self.world = world

    def key_pressed(self, _, event):
        """Called by GTK. Set input_subscriber to handle this."""
        if not self.input_subscriber: return
        val = event.keyval
        try:
            char = chr(val)
        except ValueError:
            char = ''
        self.input_subscriber.on_key_pressed(val=val, char=char)

    def mouse_moved(self, _, event):
        """Called by GTK. Set input_subscriber to handle this."""
        if not self.input_subscriber: return
        mouse_pos = Vec(event.x, event.y)
        pos_world = self.screen_to_world_pos(mouse_pos)
        self.input_subscriber.on_mouse_moved(pos=mouse_pos, pos_world=pos_world)

    def world_to_screen_pos(self, world_pos):
        return (world_pos - self.world_center) \
            .imul(self.screen_scale).iadd(self.screen_center)

    def screen_to_world_pos(self, screen_pos):
        return (screen_pos - self.screen_center) \
            .idiv(self.screen_scale).iadd(self.world_center)

    def recalculate(self):
        alloc = self.drawing_area.get_allocation()
        self.win_size.set(alloc.width, alloc.height)
        self.screen_center = self.win_size / 2
        if self.client:  # any client is focused
            window_scale = max(self.win_size.x / 1920, self.win_size.y / 1080)
            self.screen_scale = self.client.player.scale * window_scale
            self.world_center = self.client.player.center
            self.world = self.client.world
        elif self.world.size:
            self.screen_scale = min(self.win_size.x / self.world.size.x,
                                    self.win_size.y / self.world.size.y)
            self.world_center = self.world.center
        else:
            # happens when the window gets drawn before the world got updated
            self.screen_scale = 1
            self.world_center = Vec(0, 0)

    def draw(self, _, c):
        self.recalculate()

        c.set_source_rgba(*DARK_GRAY)
        c.paint()

        if self.draw_subscriber: self.draw_subscriber.on_draw_background(c, self)

        world = self.world
        wl, wt = self.world_to_screen_pos(world.top_left)
        wr, wb = self.world_to_screen_pos(world.bottom_right)

        # grid
        c.set_source_rgba(*to_rgba(LIGHT_GRAY, .3))
        line_width = c.get_line_width()
        c.set_line_width(.5)

        for y in frange(wt, wb, 50 * self.screen_scale):
            c.move_to(wl, y)
            c.line_to(wr, y)
            c.stroke()

        for x in frange(wl, wr, 50 * self.screen_scale):
            c.move_to(x, wt)
            c.line_to(x, wb)
            c.stroke()

        # world border
        c.set_line_width(4)
        c.set_source_rgba(*to_rgba(LIGHT_GRAY, .5))
        c.rectangle(wl, wt, wr-wl, wb-wt)
        c.stroke()

        c.set_line_width(line_width)

        # cells
        # reverse to show small over large cells
        for cell in sorted(world.cells.values(), reverse=True):
            pos = self.world_to_screen_pos(cell.pos)
            draw_circle(c, pos, cell.size * self.screen_scale,
                        color=to_rgba(cell.color, .8))
            if cell.is_virus or cell.is_food or cell.is_ejected_mass:
                pass  # do not draw name/size
            elif cell.name:
                draw_text_center(c, pos, '%s' % cell.name)

        if self.draw_subscriber: self.draw_subscriber.on_draw_cells(c, self)

        # HUD

        if self.draw_subscriber: self.draw_subscriber.on_draw_hud(c, self)

        # minimap
        if world.size:
            minimap_w = self.win_size.x / 5
            minimap_size = Vec(minimap_w, minimap_w)
            minimap_scale = minimap_size.x / world.size.x
            minimap_offset = self.win_size - minimap_size

            def world_to_mm(world_pos):
                return minimap_offset + (world_pos - world.top_left) * minimap_scale

            line_width = c.get_line_width()
            c.set_line_width(1)

            # minimap border
            c.set_source_rgba(*to_rgba(LIGHT_GRAY, .5))
            c.rectangle(*as_rect(minimap_offset, size=minimap_size))
            c.stroke()

            # the area visible in window
            c.rectangle(*as_rect(world_to_mm(self.screen_to_world_pos(Vec(0,0))),
                                 world_to_mm(self.screen_to_world_pos(self.win_size))))
            c.stroke()

            for cell in world.cells.values():
                draw_circle_outline(c, world_to_mm(cell.pos),
                                    cell.size * minimap_scale,
                                    color=to_rgba(cell.color, .8))

            c.set_line_width(line_width)

        # leaderboard
        lb_x = self.win_size.x - self.INFO_SIZE

        c.set_source_rgba(*to_rgba(BLACK, .6))
        c.rectangle(lb_x, 0,
                    self.INFO_SIZE, 21 * len(world.leaderboard_names))
        c.fill()

        player_cid = min(c.cid for c in self.client.player.own_cells) \
            if self.client and self.client.player.own_ids else -1
        for rank, (cid, name) in enumerate(world.leaderboard_names):
            rank += 1  # start at rank 1
            name = name or 'An unnamed cell'
            text = '%i. %s (%s)' % (rank, name, cid)
            if cid == player_cid:
                color = RED
            elif cid in world.cells:
                color = LIGHT_BLUE
            else:
                color = WHITE
            draw_text_left(c, (lb_x+10, 20*rank), text, color=color)
