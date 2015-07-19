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

from .drawutils import *
from agario.vec import Vec


class WorldViewer(object):
    """
    Draws one world and handles keys/mouse.
    Does not poll for events itself.
    Calls input_subscriber.on_{key_pressed|mouse_moved}() methods on key/mouse input.
    Calls draw_subscriber.on_draw_{background|cells|hud}() methods when drawing.
    """

    INFO_SIZE = 300

    def __init__(self, world):
        self.world = world
        self.player = None  # the focused player, or None to show full world

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

    def focus_player(self, player):
        """Follow this client regarding center and zoom."""
        self.player = player
        self.world = player.world

    def show_full_world(self, world=None):
        """
        Show the full world view instead of one client.
        :param world: optionally update the drawn world
        """
        self.player = None
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
        if self.player:  # any client is focused
            window_scale = max(self.win_size.x / 1920, self.win_size.y / 1080)
            self.screen_scale = self.player.scale * window_scale
            self.world_center = self.player.center
            self.world = self.player.world
        elif self.world.size:
            self.screen_scale = min(self.win_size.x / self.world.size.x,
                                    self.win_size.y / self.world.size.y)
            self.world_center = self.world.center
        else:
            # happens when the window gets drawn before the world got updated
            self.screen_scale = 1
            self.world_center = Vec(0, 0)

    def draw(self, _, c):
        c.set_source_rgba(*DARK_GRAY)
        c.paint()

        if self.draw_subscriber:
            self.recalculate()
            self.draw_subscriber.on_draw_background(c, self)
            self.draw_subscriber.on_draw_cells(c, self)
            self.draw_subscriber.on_draw_hud(c, self)
