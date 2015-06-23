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
    def __init__(self, channel, client, key_movement_lines=ord('l')):
        super(NativeControl, self).__init__(channel)
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

    def on_draw(self, c, w):
        if self.show_movement_lines:
            mouse_pos = w.world_to_screen_pos(self.mouse_world)
            c.set_source_rgba(*to_rgba(BLACK, .3))
            for cell in self.client.player.own_cells:
                c.move_to(*w.world_to_screen_pos(cell.pos))
                c.line_to(*mouse_pos)
                c.stroke()


# wsp, ssc
class CellInfo(Subscriber):
    def __init__(self, channel, client):
        super(CellInfo, self).__init__(channel)
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

    def on_draw(self, c, w):
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
    def __init__(self, channel, client):
        super(Logger, self).__init__(channel)
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
            try:
                print('[LOG]', msg)
            except UnicodeEncodeError:
                pass

    def on_sock_open(self):
        # remove ws://
        msg = 'Connected to %s' % self.client.url[5:]
        self.channel.broadcast('log_msg', msg=msg)
        msg = 'Token: %s' % self.client.token
        self.channel.broadcast('log_msg', msg=msg)

    def on_cell_eaten(self, eater_id, eaten_id):
        player = self.client.player
        if eaten_id in player.own_ids:
            name = 'Someone'
            if eater_id in player.world.cells:
                name = '"%s"' % player.world.cells[eater_id].name
            what = 'killed' if len(player.own_ids) <= 1 else 'ate'
            msg = '%s %s me!' % (name, what)
            self.channel.broadcast('log_msg', msg=msg)

    def on_world_update_post(self):
        player = self.client.player
        x, y = player.center
        px, py = (player.center * 100.0).ivdiv(player.world.size)
        msg = 'Size: %i Pos: (%.2f %.2f) (%i%% %i%%)' \
              % (player.total_size, x, y, round(px), round(py))
        self.channel.broadcast('log_msg', msg=msg)

    def on_own_id(self, cid):
        if len(self.client.player.own_ids) == 1:
            msg = 'Respawned as %s' % self.client.player.nick
            self.channel.broadcast('log_msg', msg=msg, update=0)
        else:
            msg = 'Split into %i cells' % len(self.client.player.own_ids)
            self.channel.broadcast('log_msg', msg=msg)

    def on_leaderboard_names(self, leaderboard):
        if not self.client.player.own_ids:
            return
        our_cid = min(c.cid for c in self.client.player.own_cells)
        for rank, (cid, name) in enumerate(leaderboard):
            if cid == our_cid:
                rank += 1  # start at rank 1
                self.leader_max = min(rank, self.leader_max)
                msg = 'Leaderboard: %i. (top: %i.)' % (rank, self.leader_max)
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

        self.channel_draw_world = Channel()
        self.channel_draw_hud = Channel()

        NativeControl(self.channel_draw_world, client)
        CellInfo(self.channel_draw_world, client)

        Logger(self.channel_draw_hud, client)
        MassGraph(self.channel_draw_hud, client)
        FpsMeter(self.channel_draw_hud, 50)

        for sub in self.channel_draw_world.subscribers \
                + self.channel_draw_hud.subscribers:
            client.channel.subscribe(sub)

        client.connect_retry()

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
        elif char == 's':
            self.client.send_spectate()
        elif char == 'r':
            self.client.send_respawn()
        elif char == 'c':  # reconnect to any server
            self.client.disconnect()
            self.client.player.nick = random.choice(special_names)
            self.client.connect_retry()

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
        c.set_source_rgba(*DARK_GRAY)
        c.paint()

        player = self.client.player
        world = player.world

        # window may have been resized
        alloc = self.window.get_allocation()
        self.win_w, self.win_h = alloc.width, alloc.height
        self.win_size.set(self.win_w, self.win_h)
        self.screen_center = self.win_size / 2
        self.screen_scale = player.scale * max(self.win_w / 1920, self.win_h / 1080)

        # XXX show whole world
        # self.screen_scale = min(self.win_h / self.world_size,
        #                         self.win_w / self.world_size)
        # self.world_center = self.world_size / 2

        wl, wt = self.world_to_screen_pos(Vec())
        wr, wb = self.world_to_screen_pos(world.size)

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
        c.rectangle(wl, wt, *(world.size * self.screen_scale))
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

        self.channel_draw_world.broadcast('draw', c=c, w=self)

        # minimap
        if world.size.x != 0:
            minimap_size = self.win_w / 5
            line_width = c.get_line_width()
            c.set_line_width(1)

            c.set_source_rgba(*to_rgba(LIGHT_GRAY, .5))
            c.rectangle(self.win_w-minimap_size, self.win_h-minimap_size,
                        *(minimap_size,)*2)
            c.stroke()

            minimap_scale = minimap_size / world.size.x
            for cell in world.cells.values():
                pos = Vec(self.win_w-minimap_size, self.win_h-minimap_size)
                draw_circle_outline(c, pos.iadd(cell.pos * minimap_scale),
                                    cell.size * minimap_scale,
                                    color=to_rgba(cell.color, .8))

            c.set_line_width(line_width)

        self.channel_draw_hud.broadcast('draw', c=c, w=self)

        # leaderboard
        lb_x = self.win_w - self.INFO_SIZE

        c.set_source_rgba(*to_rgba(BLACK, .6))
        c.rectangle(lb_x - 10, 0,
                    self.INFO_SIZE, 21 * len(world.leaderboard_names))
        c.fill()

        player_cid = min(c.cid for c in player.own_cells) \
            if player.own_ids else -1
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
            draw_text_left(c, (lb_x, 20*rank), text, color=color)

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
