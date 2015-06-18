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
from collections import deque

import random
from time import time
from gi.repository import Gtk, GLib, Gdk
from client import Client, special_names
from drawing_helpers import *
from event import Channel, Subscriber
from vec import Vec


def frange(start, end, step):
    while start < end:
        yield start
        start += step


class NativeControl(Subscriber):
    def __init__(self, channel, client):
        super(NativeControl, self).__init__(channel)
        self.client = client
        self.movement_delta = Vec()

    @property
    def mouse_world(self):
        return self.client.player.center + self.movement_delta

    def send_mouse(self):
        self.client.send_mouse(*self.mouse_world)

    def on_world_update_post(self):
        self.send_mouse()

    def on_mouse_moved(self, pos, pos_world):
        self.movement_delta = pos_world - self.client.player.center
        self.send_mouse()

    def on_key_pressed(self, val, char):
        if char == 'w':
            self.send_mouse()
            self.client.send_shoot()
        elif val == Gdk.KEY_space:
            self.send_mouse()
            self.client.send_split()

    def on_draw(self, c, w):
        if w.show_debug:
            # movement lines
            mouse_pos = w.world_to_screen_pos(self.mouse_world)
            for cid in self.client.player.own_ids:
                cell = self.client.world.cells[cid]
                x, y = w.world_to_screen_pos(cell.pos)
                c.set_source_rgba(*to_rgba(FUCHSIA, .3))
                c.move_to(x, y)
                c.line_to(*mouse_pos)
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
        self.channel = channel
        self.client = client
        self.log_msgs = []
        self.leader_max = -1

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
        msg = 'Connected as "%s" to %s' % (self.client.player.nick, ip)
        self.channel.broadcast('log_msg', msg=msg)

    def on_cell_eaten(self, eater_id, eaten_id):
        if eaten_id in self.client.player.own_ids:
            mass = self.client.world.cells[eater_id].mass
            name = 'Someone'
            if eater_id in self.client.world.cells:
                name = '"%s"' % self.client.world.cells[eater_id].name
            msg = '%s ate me! (%i mass)' % (name, mass)
            self.channel.broadcast('log_msg', msg=msg)

    def on_world_update_post(self):
        x, y = self.client.player.center
        px, py = (self.client.player.center * 100.0).ivdiv(self.client.world.size)
        msg = 'Size: %i Pos: (%.2f %.2f) (%i%% %i%%)' \
              % (self.client.player.total_size, x, y, round(px), round(py))
        self.channel.broadcast('log_msg', msg=msg)

    def on_own_id(self, cid):
        if len(self.client.player.own_ids) == 1:
            self.channel.broadcast('log_msg', msg='Respawned', update=0)

    def on_leaderboard_names(self, leaderboard):
        if not self.client.player.own_ids:
            return
        our_cid = min(c.cid for c in self.client.player.own_cells)
        for i, (cid, name) in enumerate(leaderboard):
            if cid == our_cid:
                self.leader_max = max(i, self.leader_max)
                msg = 'Leaderboard: %i. (top: %i.)' % (i, self.leader_max)
                self.channel.broadcast('log_msg', msg=msg)

    def on_draw(self, c, w):
        # scrolling log
        log_line_h = 12
        log_char_w = 6  # seems to work with my font

        log = list(format_log(self.log_msgs, w.INFO_SIZE / log_char_w))
        num_log_lines = min(len(log), int(w.INFO_SIZE / log_line_h))

        y_start = w.win_h - num_log_lines*log_line_h + 9

        c.set_source_rgba(*to_rgba(BLACK, .3))
        c.rectangle(0, w.win_h - num_log_lines*log_line_h,
                    w.INFO_SIZE, num_log_lines*log_line_h)
        c.fill()

        for i, text in enumerate(log[-num_log_lines:]):
            draw_text_left(c, (0, y_start + i*log_line_h),
                           text, size=10, face='monospace')


class MassGraph(Subscriber):
    def __init__(self, channel, client):
        super(MassGraph, self).__init__(channel)
        self.client = client
        self.graph = []

    def on_respawn(self):
        self.graph.clear()

    def on_world_update_post(self):
        player = self.client.player
        if not player.is_alive:
            return
        sample = (
            player.total_mass,
            sorted((c.cid, c.mass) for c in player.own_cells)
        )
        self.graph.append(sample)

    def on_draw(self, c, w):
        if not self.graph:
            return
        scale_x = w.INFO_SIZE / len(self.graph)
        scale_y = w.INFO_SIZE / (max(self.graph)[0] or 10)
        c.set_source_rgba(*to_rgba(BLUE, .3))
        c.move_to(0, 0)
        for i, (total_mass, masses) in enumerate(reversed(self.graph)):
            c.line_to(i * scale_x, total_mass * scale_y)
        c.line_to(w.INFO_SIZE, 0)
        c.fill()


class FpsMeter(Subscriber):
    def __init__(self, channel, queue_len, toggle_key=Gdk.KEY_F3):
        super(FpsMeter, self).__init__(channel)
        self.draw_last = self.world_last = time()
        self.draw_times = deque([0]*queue_len, queue_len)
        self.world_times = deque([0]*queue_len, queue_len)
        self.toggle_key = toggle_key
        self.show = False

    def on_key_pressed(self, val, char):
        if val == self.toggle_key:
            self.show = not self.show

    def on_world_update_post(self):
        now = time()
        dt = now - self.world_last
        self.world_last = now
        self.world_times.appendleft(dt)

    def on_draw(self, c, w):
        if self.show:
            c.set_source_rgba(*to_rgba(RED, .3))
            for i, t in enumerate(self.draw_times):
                c.move_to(w.win_w - 4*i - 2, w.win_h)
                c.rel_line_to(0, -t * 1000)
                c.stroke()

            c.set_source_rgba(*to_rgba(YELLOW, .3))
            for i, t in enumerate(self.world_times):
                c.move_to(w.win_w - 4*i, w.win_h)
                c.rel_line_to(0, -t * 1000)
                c.stroke()

        now = time()
        dt = now - self.draw_last
        self.draw_last = now
        self.draw_times.appendleft(dt)


class AgarWindow:
    INFO_SIZE = 300

    def __init__(self):
        self.show_debug = False
        self.win_w, self.win_h = self.win_size = Vec(1000, 1000 * 9 / 16)
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

        self.client = client = Client()
        client.player.nick = random.choice(special_names)

        Logger(client.channel, client)
        NativeControl(client.channel, client)
        MassGraph(client.channel, client)
        FpsMeter(client.channel, 50)

        client.connect()
        # self.client.connect('ws://localhost:443')
        # self.client.connect('ws://213.168.251.152:443')

        # watch socket in GTK main loop
        # `or True` is for always returning True to keep watching
        GLib.io_add_watch(client.ws, GLib.IO_IN, lambda ws, _:
                          client.on_message() or True)
        GLib.io_add_watch(client.ws, GLib.IO_ERR, lambda _, __:
                          client.channel.broadcast('sock_error') or True)
        GLib.io_add_watch(client.ws, GLib.IO_HUP, lambda _, __:
                          client.disconnect() or True)

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
        mouse_pos = Vec(event.x, event.y)
        self.client.channel.broadcast('mouse_moved', pos=mouse_pos,
                                pos_world=self.screen_to_world_pos(mouse_pos))

    def world_to_screen_pos(self, pos):
        return (pos - self.client.player.center) \
            .imul(self.screen_scale).iadd(self.screen_center)

    def screen_to_world_pos(self, pos):
        return (pos - self.screen_center) \
            .idiv(self.screen_scale).iadd(self.client.player.center)

    def draw(self, _, c):
        c.set_source_rgba(*DARKGRAY)
        c.paint()

        client = self.client
        world = client.world

        # window may have been resized
        alloc = self.window.get_allocation()
        self.win_w, self.win_h = alloc.width, alloc.height
        self.win_size.set(self.win_w, self.win_h)
        self.screen_center = self.win_size / 2
        self.screen_scale = client.player.scale \
                            * max(self.win_w / 1920, self.win_h / 1080)

        # XXX show whole world
        # self.screen_scale = min(self.win_h / self.world_size,
        #                         self.win_w / self.world_size)
        # self.world_center = self.world_size / 2

        wl, wt = self.world_to_screen_pos(Vec())
        wr, wb = self.world_to_screen_pos(world.size)

        # grid
        c.set_source_rgba(*to_rgba(LIGHTGRAY, .3))
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
        c.set_source_rgba(*to_rgba(LIGHTGRAY, .5))
        c.rectangle(wl, wt, *(world.size * self.screen_scale))
        c.stroke()

        c.set_line_width(line_width)

        # cells
        # normal: show large over small, debug: show small over large
        for cell in sorted(world.cells.values(),
                           reverse=self.show_debug):
            x, y = pos = self.world_to_screen_pos(cell.pos)
            draw_circle(c, pos, cell.size * self.screen_scale,
                        color=to_rgba(cell.color, .8))
            if cell.is_virus or cell.is_food or cell.is_ejected_mass:
                pass  # do not draw name/size
            elif cell.name:
                draw_text_center(c, pos, '%s' % cell.name)
                if self.show_debug:
                    draw_text_center(c, (x, y + 12), '%i' % cell.mass)
            elif self.show_debug:
                draw_text_center(c, pos, '%i' % cell.mass)

        # draw handlers
        client.channel.broadcast('draw', c=c, w=self)

        # leaderboard
        lb_x = self.win_w - self.INFO_SIZE

        c.set_source_rgba(*to_rgba(BLACK, .6))
        c.rectangle(lb_x - 10, 0,
                    self.INFO_SIZE, 21 * len(world.leaderboard_names))
        c.fill()

        player_cid = min(c.cid for c in client.player.own_cells) \
            if client.player.own_ids else -1
        for i, (cid, name) in enumerate(world.leaderboard_names):
            name = name or 'An unnamed cell'
            text = '%i. %s (%s)' % (i+1, name, cid)
            color = RED if cid == player_cid else WHITE
            draw_text_left(c, (lb_x, 20*(i+1)), text, color=color)

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
