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

import random
from gi.repository import Gtk, GLib, Gdk
from client import Client, special_names
from drawing_helpers import *
from event import Channel, Subscriber
from vec import Vec


class NativeControl(Subscriber):
    def __init__(self, channel, client):
        super(NativeControl, self).__init__(channel)
        self.client = client
        self.movement_delta = Vec()

    @property
    def mouse_world(self):
        return self.client.player.center + self.movement_delta

    def on_world_update_post(self):
        self.client.send_mouse(*self.mouse_world)

    def on_mouse_moved(self, pos, pos_world):
        self.movement_delta = pos_world - self.client.player.center
        self.client.send_mouse(*self.mouse_world)

    def on_key_pressed(self, val, char):
        if char == 'w':
            self.client.send_mouse(*self.mouse_world)
            self.client.send_shoot()
        elif val == Gdk.KEY_space:
            self.client.send_mouse(*self.mouse_world)
            self.client.send_split()

    def on_draw(self, c, w):
        if w.show_debug:
            # movement lines
            for cid in self.client.player.own_ids:
                cell = self.client.world.cells[cid]
                x, y = w.world_to_screen_pos(cell.pos)
                c.set_source_rgba(*to_rgba(FUCHSIA, .3))
                c.move_to(x, y)
                c.line_to(*w.world_to_screen_pos(self.mouse_world))
                c.stroke()


def format_log(lines, width, indent='  '):
    width = int(width)
    for l in lines:
        ind = ''
        while len(l) > len(ind):
            yield l[:width]
            ind = indent
            l = ind + l[width:]


class Logger(Subscriber):
    def __init__(self, channel, client):
        super(Logger, self).__init__(channel)
        self.client = client
        self.log_msgs = []

    def on_log_msg(self, msg, update=9):
        """
        Updates up to 9th-last msg with new data.
        Compares first 5 chars or up to first space.
        Set update=0 for no updating.
        """
        first_space = msg.index(' ') if ' ' in msg else 5
        for i, log_msg in enumerate(reversed(
                self.log_msgs[-update:] if update else [])):
            if msg[:first_space] == log_msg[:first_space]:
                self.log_msgs[-i - 1] = msg
                break
        else:
            self.log_msgs.append(msg)
            print('[LOG]', msg)

    def on_sock_open(self):
        # remove ws://
        ip = self.client.url[5:]
        self.client.channel.broadcast('log_msg', msg='Connected as "%s" to %s'
                                      % (self.client.player.nick, ip))

    def on_cell_eaten(self, eater_id, eaten_id):
        if eaten_id in self.client.player.own_ids:
            name = 'Someone'
            if eater_id in self.client.world.cells:
                name = '"%s"' % self.client.world.cells[eater_id].name
            self.client.channel.broadcast('log_msg', msg='%s ate me!' % name)

    def on_world_update_post(self):
        x, y = self.client.player.center
        px, py = (self.client.player.center * 100.0).ivdiv(self.client.world.size)
        msg = 'Size: %i Pos: (%.2f %.2f) (%i%% %i%%)' \
              % (self.client.player.total_size, x, y, round(px), round(py))
        self.client.channel.broadcast('log_msg', msg=msg)

    def on_own_id(self, cid):
        if len(self.client.player.own_ids) == 1:
            self.client.channel.broadcast('log_msg', msg='Respawned', update=0)

    def on_draw(self, c, w):
        # scrolling log
        log_line_h = 12
        log_char_w = 6  # seems to work with my font

        log = list(format_log(self.log_msgs,
                              w.LOG_W / log_char_w))
        num_log_lines = min(len(log), int(w.win_h / log_line_h))

        y_start = w.win_h - num_log_lines*log_line_h + 9

        c.set_source_rgba(0,0,0, .3)
        c.rectangle(0, w.win_h - num_log_lines*log_line_h,
                    w.LOG_W, num_log_lines*log_line_h)
        c.fill()

        for i, text in enumerate(log[-num_log_lines:]):
            draw_text_left(c, (0, y_start + i*log_line_h),
                           text, size=10, face='monospace')


class AgarWindow:
    LOG_W = 300

    def __init__(self):
        self.show_debug = False
        self.win_w, self.win_h = self.win_size = Vec(1000, 1000 * 9 / 16)
        self.mouse_pos = Vec()
        self.screen_center = self.win_size / 2
        self.screen_scale = max(self.win_w / 1920, self.win_h / 1080)

        self.window = Gtk.Window()
        self.window.set_title('agar.io')
        self.window.set_default_size(self.win_w, self.win_h)
        self.window.connect('delete-event', Gtk.main_quit)

        drawing_area = Gtk.DrawingArea()
        self.window.add(drawing_area)

        self.window.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.window.connect('key-press-event', self.on_key_pressed)
        self.window.connect('motion-notify-event', self.on_mouse_moved)
        drawing_area.connect('draw', self.draw)

        GLib.timeout_add(50, self.tick, drawing_area)

        self.client = Client()
        self.client.player.nick = random.choice(special_names)

        Logger(self.client.channel, self.client)
        NativeControl(self.client.channel, self.client)

        self.client.connect()
        # self.client.connect('ws://localhost:443')
        # self.client.connect('ws://213.168.251.152:443')

        # watch socket in GTK main loop
        # `or True` is for always returning True to keep watching
        GLib.io_add_watch(self.client.ws, GLib.IO_IN, lambda ws, _:
                          self.client.on_message() or True)
        GLib.io_add_watch(self.client.ws, GLib.IO_ERR, lambda _, __:
                          self.client.channel.broadcast('sock_error') or True)
        GLib.io_add_watch(self.client.ws, GLib.IO_HUP, lambda _, __:
                          self.client.disconnect() or True)

        self.window.show_all()

        # Gtk.main() swallows exceptions, get them back
        import sys
        sys.excepthook = lambda *args: sys.__excepthook__(*args) or sys.exit()

        Gtk.main()

    def on_key_pressed(self, _, event):
        val = event.keyval
        try:
            char = chr(val)
        except ValueError:
            char = ''
        if char == 'q' or val == Gdk.KEY_Escape:
            self.client.disconnect()
            Gtk.main_quit()
        elif char == 'h':
            self.show_debug = not self.show_debug
        elif char == 's':
            self.client.send_spectate()
        elif char == 'r':
            self.client.send_respawn()
        elif char == 'c':
            self.client.disconnect()
            self.client.connect()
        elif char == 'k':
            url = self.client.url
            self.client.disconnect()
            self.client.connect(url)

        self.client.channel.broadcast('key_pressed', val=val, char=char)

    def on_mouse_moved(self, _, event):
        self.mouse_pos.set(event.x, event.y)
        self.client.channel.broadcast('mouse_moved', pos=self.mouse_pos,
                                      pos_world=self.screen_to_world_pos(
                                          self.mouse_pos))

    def world_to_screen_pos(self, pos):
        return self.screen_center \
               + (self.screen_scale * (pos - self.client.player.center))

    def screen_to_world_pos(self, pos):
        return self.client.player.center \
               + (self.screen_scale * (pos - self.screen_center))

    def draw(self, _, c):
        c.set_source_rgba(*DARKGRAY)
        c.paint()

        # window may have been resized
        alloc = self.window.get_allocation()
        self.win_w, self.win_h = alloc.width, alloc.height
        self.win_size.set(self.win_w, self.win_h)
        self.screen_center = self.win_size / 2
        self.screen_scale = self.client.player.scale \
                            * max(self.win_w / 1920, self.win_h / 1080)

        # XXX show whole world
        # self.screen_scale = min(self.win_h / self.world_size,
        #                         self.win_w / self.world_size)
        # self.world_center = self.world_size / 2

        wl, wt = self.world_to_screen_pos(Vec())
        wr, wb = self.world_to_screen_pos(self.client.world.size)

        # grid
        c.set_source_rgba(*to_rgba(LIGHTGRAY, .3))
        line_width = c.get_line_width()
        c.set_line_width(.5)

        for y in range(int(wt), int(wb), int(50 * self.screen_scale)):
            c.move_to(wl, y)
            c.line_to(wr, y)
            c.stroke()

        for x in range(int(wl), int(wr), int(50 * self.screen_scale)):
            c.move_to(x, wt)
            c.line_to(x, wb)
            c.stroke()

        # world border
        c.set_line_width(4)
        c.set_source_rgba(*to_rgba(LIGHTGRAY, .5))
        c.rectangle(wl, wt, *(self.client.world.size * self.screen_scale))
        c.stroke()

        c.set_line_width(line_width)

        # cells
        # normal: show large over small, debug: show small over large
        for cell in sorted(self.client.world.cells.values(),
                key=lambda cell: cell.size, reverse=self.show_debug):
            x, y = pos = self.world_to_screen_pos(cell.pos)
            draw_circle(c, pos, cell.size * self.screen_scale,
                        color=to_rgba(cell.color, .8))
            # name, size
            if cell.is_virus or cell.size < 20:  # food <= 11 < 30 <= cells
                pass  # do not draw name/size
            elif cell.is_agitated and self.show_debug:
                draw_text_center(c, pos, '(agitated)')
                draw_text_center(c, (x, y + 12), '%i' % cell.size)
            elif cell.name:
                draw_text_center(c, pos, '%s' % cell.name)
                if self.show_debug:
                    draw_text_center(c, (x, y + 12), '%i' % cell.size)
            elif self.show_debug:
                draw_text_center(c, pos, '%i' % cell.size)

        # draw handlers
        self.client.channel.broadcast('draw', c=c, w=self)

        # leaderboard
        lb_x = self.win_w - self.LOG_W

        c.set_source_rgba(0,0,0, .6)
        c.rectangle(lb_x - 10, 0,
                    self.LOG_W, 21 * len(self.client.world.leaderboard_names))
        c.fill()

        for i, (points, name) in enumerate(self.client.world.leaderboard_names):
            name = name or 'An unnamed cell'
            text = '%i. %s (%s)' % (i+1, name, points)
            draw_text_left(c, (lb_x, 20*(i+1)), text)

    def tick(self, drawing_area):
        # TODO no ticking, only draw when server sends world update
        self.client.channel.broadcast('tick')
        drawing_area.queue_draw()
        return True


if __name__ == '__main__':
    print('Copyright (C) 2015  Gjum  <code.gjum@gmail.com>')
    print("This program comes with ABSOLUTELY NO WARRANTY.\n"
          "This is free software, and you are welcome to redistribute it\n"
          "under certain conditions; see LICENSE.txt for details.")
    AgarWindow()
