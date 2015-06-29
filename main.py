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
from subscriber import MultiSubscriber, Subscriber
from vec import Vec
from window import WorldViewer


class NativeControl(Subscriber):
    def __init__(self, client, key_movement_lines=ord('l')):
        self.client = client
        self.movement_delta = Vec()
        self.show_movement_lines = True
        self.key_movement_lines = key_movement_lines

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
        elif char == 'k':
            self.client.send_explode()
        elif val == self.key_movement_lines:
            self.show_movement_lines = not self.show_movement_lines

    def on_draw_cells(self, c, w):
        if self.show_movement_lines:
            mouse_pos = w.world_to_screen_pos(self.mouse_world)
            c.set_source_rgba(*to_rgba(BLACK, .3))
            for cell in self.client.player.own_cells:
                c.move_to(*w.world_to_screen_pos(cell.pos))
                c.line_to(*mouse_pos)
                c.stroke()


class CellInfo(Subscriber):
    def __init__(self, client):
        self.client = client
        self.show_cell_masses = False
        self.show_remerge_times = False
        self.show_hostility = False
        self.cell_masses_key = ord('h')
        self.remerge_times_key = ord('h')
        self.hostility_key = ord('h')

    def on_key_pressed(self, val, char):
        if val == self.cell_masses_key:
            self.show_cell_masses = not self.show_cell_masses
        if val == self.remerge_times_key:
            self.show_remerge_times = not self.show_remerge_times
        if val == self.hostility_key:
            self.show_hostility = not self.show_hostility

    def on_own_id(self, cid):
        self.client.player.world.cells[cid].split_time = time()

    def on_draw_cells(self, c, w):
        p = self.client.player
        if self.show_cell_masses:
            self.draw_cell_masses(c, w, p)
        if self.show_remerge_times:
            self.draw_remerge_times(c, w, p)
        if self.show_hostility:
            self.draw_hostility(c, w, p)

    def draw_cell_masses(self, c, w, p):
        for cell in p.world.cells.values():
            if cell.is_food or cell.is_ejected_mass:
                continue
            pos = w.world_to_screen_pos(cell.pos)
            if cell.name:
                pos.iadd(Vec(0, 12))
            text = '%i mass' % cell.mass
            draw_text_center(c, pos, text)

    def draw_remerge_times(self, c, w, p):
        if len(p.own_ids) <= 1:
            return  # dead or only one cell, no remerge time to display
        now = time()
        for cell in p.own_cells:
            split_for = now - cell.split_time
            # formula by DebugMonkey
            ttr = (p.total_mass * 20 + 30000) / 1000 - split_for
            if ttr < 0: continue
            pos = w.world_to_screen_pos(cell.pos)
            text = 'TTR %.1fs after %.1fs' % (ttr, split_for)
            draw_text_center(c, Vec(0, -12).iadd(pos), text)

    def draw_hostility(self, c, w, p):
        if not p.is_alive: return  # nothing to be hostile against
        own_min_mass = min(c.mass for c in p.own_cells)
        own_max_mass = max(c.mass for c in p.own_cells)
        lw = c.get_line_width()
        c.set_line_width(5)
        for cell in p.world.cells.values():
            if cell.is_food or cell.is_ejected_mass:
                continue  # no threat
            if cell.cid in p.own_ids:
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
            draw_circle_outline(c, pos, cell.size * w.screen_scale)
        c.set_line_width(lw)


def format_log(lines, width, indent='  '):
    width = int(width)
    for l in lines:
        ind = ''
        while len(l) > len(ind):
            yield l[:width]
            ind = indent
            l = ind + l[width:]


class Logger(Subscriber):
    def __init__(self, client):
        self.client = client
        self.log_msgs = []
        self.leader_best = 11 # outside leaderboard, to show first msg on >=10

    def on_log_msg(self, msg, update=0):
        """
        Updates last `update` msgs with new data.
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
            try:
                print('[LOG]', msg)
            except UnicodeEncodeError:
                pass

    def on_update_msg(self, msg, update=9):
        self.on_log_msg(msg=msg, update=update)

    def on_sock_open(self):
        # remove ws://
        self.on_update_msg('Connected to %s' % self.client.url[5:])
        self.on_update_msg('Token: %s' % self.client.token)

    def on_world_rect(self, **kwargs):
        self.on_update_msg('World is from %(left)i:%(top)i to %(right)i:%(bottom)i' % kwargs)

    def on_cell_eaten(self, eater_id, eaten_id):
        player = self.client.player
        if eaten_id in player.own_ids:
            name = 'Someone'
            if eater_id in player.world.cells:
                name = '"%s"' % player.world.cells[eater_id].name
            what = 'killed' if len(player.own_ids) <= 1 else 'ate'
            msg = '%s %s me!' % (name, what)
            self.on_update_msg(msg)

    def on_world_update_post(self):
        player = self.client.player
        x, y = player.center
        self.on_update_msg('Size: %i Pos: (%.2f %.2f)' % (player.total_size, x, y))

    def on_own_id(self, cid):
        if len(self.client.player.own_ids) == 1:
            self.on_log_msg('Respawned as %s' % self.client.player.nick)
        else:
            self.on_update_msg('Split into %i cells' % len(self.client.player.own_ids))

    def on_leaderboard_names(self, leaderboard):
        if not self.client.player.own_ids:
            return
        our_cid = min(c.cid for c in self.client.player.own_cells)
        for rank, (cid, name) in enumerate(leaderboard):
            if cid == our_cid:
                rank += 1  # start at rank 1
                self.leader_best = min(rank, self.leader_best)
                msg = 'Leaderboard: %i. (best: %i.)' % (rank, self.leader_best)
                self.on_update_msg(msg)

    def on_draw_hud(self, c, w):
        # scrolling log
        log_line_h = 12
        log_char_w = 6  # seems to work with my font

        log = list(format_log(self.log_msgs, w.INFO_SIZE / log_char_w))
        num_log_lines = min(len(log), int(w.INFO_SIZE / log_line_h))

        y_start = w.win_size.y - num_log_lines*log_line_h + 9

        c.set_source_rgba(*to_rgba(BLACK, .3))
        c.rectangle(0, w.win_size.y - num_log_lines*log_line_h,
                    w.INFO_SIZE, num_log_lines*log_line_h)
        c.fill()

        for i, text in enumerate(log[-num_log_lines:]):
            draw_text_left(c, (0, y_start + i*log_line_h),
                           text, size=10, face='monospace')


class MassGraph(Subscriber):
    def __init__(self, client):
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

    def on_draw_hud(self, c, w):
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
    def __init__(self, queue_len, toggle_key=Gdk.KEY_F3):
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

    def on_draw_hud(self, c, w):
        if self.show:
            c.set_source_rgba(*to_rgba(RED, .3))
            for i, t in enumerate(self.draw_times):
                c.move_to(*(w.win_size - Vec(4*i - 2, 0)))
                c.rel_line_to(0, -t * 1000)
                c.stroke()

            c.set_source_rgba(*to_rgba(YELLOW, .3))
            for i, t in enumerate(self.world_times):
                c.move_to(*(w.win_size - Vec(4*i, 0)))
                c.rel_line_to(0, -t * 1000)
                c.stroke()

        now = time()
        dt = now - self.draw_last
        self.draw_last = now
        self.draw_times.appendleft(dt)


def gtk_watch_client(client):
    # watch clinet's websocket in GTK main loop
    # `or True` is for always returning True to keep watching
    GLib.io_add_watch(client.ws, GLib.IO_IN, lambda ws, _: client.on_message() or True)
    GLib.io_add_watch(client.ws, GLib.IO_ERR, lambda ws, __: client.subscriber.on_sock_error() or True)
    GLib.io_add_watch(client.ws, GLib.IO_HUP, lambda ws, __: client.disconnect() or True)


def gtk_main_loop():
    # Gtk.main() swallows exceptions, get them back
    import sys
    sys.excepthook = lambda *args: sys.__excepthook__(*args) or sys.exit()

    Gtk.main()


class GtkControl(Subscriber):
    def __init__(self, url=None, token=None):
        multi_sub = MultiSubscriber(self)

        self.client = client = Client(multi_sub)

        multi_sub.sub(NativeControl(client))
        multi_sub.sub(CellInfo(client))

        multi_sub.sub(Logger(client))
        multi_sub.sub(MassGraph(client))
        multi_sub.sub(FpsMeter(50))

        client.player.nick = random.choice(special_names)
        client.connect_retry(url, token)

        gtk_watch_client(client)

        self.world_viewer = wv = WorldViewer(client.world)
        wv.draw_subscriber = wv.input_subscriber = multi_sub
        wv.focus_client(client)

    def on_world_update_post(self):
        self.world_viewer.drawing_area.queue_draw()

    def on_key_pressed(self, val, char):
        if char == 'q' or val == Gdk.KEY_Escape:
            self.client.disconnect()
            Gtk.main_quit()
        elif char == 's':
            self.client.send_spectate()
        elif char == 'r':
            self.client.send_respawn()
        elif char == 'c':  # reconnect to any server
            self.client.disconnect()
            self.client.player.nick = random.choice(special_names)
            self.client.connect_retry()


if __name__ == '__main__':
    print("Copyright (C) 2015  Gjum  <code.gjum@gmail.com>\n"
          "This program comes with ABSOLUTELY NO WARRANTY.\n"
          "This is free software, and you are welcome to redistribute it\n"
          "under certain conditions; see LICENSE.txt for details.\n")

    GtkControl()
    gtk_main_loop()
