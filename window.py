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
from client import AgarClient, Handler, special_names

TWOPI = 6.28

def to_rgba(c, a):
    return c[0], c[1], c[2], a

BLACK = (0,0,0)
WHITE = (1,1,1)
DARKGRAY = (.2,)*3
LIGHTGRAY = (.7,)*3
BLUE = (.2,.2,1)
FUCHSIA = (1,0,1)

def format_log(lines, width, indent='  '):
    width = int(width)
    for l in lines:
        ind = ''
        while len(l) > len(ind):
            yield l[:width]
            ind = indent
            l = ind + l[width:]

def draw_text_center(c, center, text, *args, **kwargs):
    try:
        x_bearing, y_bearing, text_width, text_height, x_advance, y_advance \
            = c.text_extents(text)
        cx, cy = center
        x = cx - x_bearing - text_width / 2
        y = cy - y_bearing - text_height / 2
        draw_text_left(c, (x, y), text, *args, **kwargs)
    except UnicodeEncodeError:
        pass

def draw_text_left(c, pos, text,
                   color=WHITE, shadow=None, size=12, face='sans'):
    try:
        c.select_font_face(face)
        c.set_font_size(size)
        x, y = pos
        if shadow:
            s_color, s_offset = shadow
            s_dx, s_dy = s_offset
            c.move_to(x + s_dx, y + s_dy)
            c.set_source_rgba(*s_color)
            c.show_text(text)
        c.move_to(x, y)
        c.set_source_rgba(*color)
        c.show_text(text)
    except UnicodeEncodeError:
        pass

def pos_xy(o):
    return o.x, o.y

class NativeControlHandler(Handler):

    def __init__(self, client):
        super().__init__(client)
        self.movement_delta = 0,0

    @property
    def mouse_world(self):
        cx, cy = self.client.center
        dx, dy = self.movement_delta
        return cx + dx, cy + dy

    def on_key_pressed(self, val, char):
        if char == 'w':
            self.client.send_shoot()
        elif val == Gdk.KEY_space:
            self.client.send_split()

    def on_mouse_moved(self, pos, pos_world):
        wx, wy = pos_world
        cx, cy = self.client.center
        self.movement_delta = wx - cx, wy - cy
        self.client.send_mouse(*self.mouse_world)

    def on_world_update_post(self):
        self.client.send_mouse(*self.mouse_world)

    def on_draw(self, c, w):
        if w.show_debug:
            # movement lines
            for cid in self.client.own_ids:
                cell = self.client.cells[cid]
                x, y = w.world_to_screen_pos(pos_xy(cell))
                c.set_source_rgba(*to_rgba(FUCHSIA, .3))
                c.move_to(x,y)
                c.line_to(*w.world_to_screen_pos(self.mouse_world))
                c.stroke()

class LoggingHandler(Handler):

    def __init__(self, client):
        super().__init__(client)
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
                self.log_msgs[-i-1] = msg
                break
        else:
            self.log_msgs.append(msg)
            print('[LOG]', msg)

    def on_sock_open(self):
        # remove ws:// and :433 part
        ip = self.client.url[5:-4]
        self.client.handle('log_msg', msg='Connected as "%s" to %s' % (self.client.nick, ip))

    def on_cell_eaten(self, eater_id, eaten_id):
        if eaten_id in self.client.own_ids:
            name = 'Someone'
            if eater_id in self.client.cells:
                name = '"%s"' % self.client.cells[eater_id].name
            self.client.handle('log_msg', msg='%s ate me!' % name)

    def on_world_update_post(self):
        x, y = self.client.center
        px, py = x*100/self.client.world_size, y*100/self.client.world_size
        self.client.handle('log_msg', msg='Size: %i Pos: (%.2f %.2f) (%i%% %i%%)'
                     % (self.client.total_size, x, y, round(px), round(py)))

    def on_own_id(self, cid):
        if len(self.client.own_ids) == 1:
            self.client.handle('log_msg', msg='Respawned', update=0)

    def on_draw(self, c, w):
        # scrolling log
        log_line_h = 12
        log_char_w = 6  # seems to work with my font

        log = list(format_log(self.log_msgs,
                              w.LOG_W/log_char_w))
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
        self.win_w, self.win_h = 1000, 1000 * 9 / 16
        self.mouse_pos = 0,0
        self.screen_center = self.win_w / 2, self.win_h / 2
        self.screen_scale = max(self.win_h / 1080, self.win_w / 1920)

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

        self.client = AgarClient()
        self.client.nick = random.choice(special_names)

        LoggingHandler(self.client)
        NativeControlHandler(self.client)

        self.client.connect()

        # check socket in GTK main loop
        GLib.io_add_watch(self.client.ws, GLib.IO_IN, lambda ws, _:
                          self.client.on_message() or True)
        GLib.io_add_watch(self.client.ws, GLib.IO_ERR, lambda _, __:
                          self.client.handle('sock_error') or True)
        GLib.io_add_watch(self.client.ws, GLib.IO_HUP, lambda _, __:
                          self.client.handle('sock_closed') or True)

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

        self.client.handle('key_pressed', val=val, char=char)

    def on_mouse_moved(self, _, event):
        self.mouse_pos = pos_xy(event)
        self.client.handle('mouse_moved', pos=self.mouse_pos,
                           pos_world=self.screen_to_world_pos(self.mouse_pos))

    def world_to_screen_pos(self, pos):
        wx, wy = self.client.center
        sx, sy = self.screen_center
        x, y = pos
        x = (x-wx) * self.screen_scale + sx
        y = (y-wy) * self.screen_scale + sy
        return x, y

    def screen_to_world_pos(self, pos):
        wx, wy = self.client.center
        sx, sy = self.screen_center
        x, y = pos
        x = (x-sx) * self.screen_scale + wx
        y = (y-sy) * self.screen_scale + wy
        return x, y

    def draw(self, _, c):
        c.set_source_rgba(*DARKGRAY)
        c.paint()

        alloc = self.window.get_allocation()
        self.win_w, self.win_h = alloc.width, alloc.height
        self.screen_center = self.win_w / 2, self.win_h / 2

        self.screen_scale = self.client.scale \
                            * max(self.win_h / 1080, self.win_w / 1920)

        # grid
        c.set_source_rgba(*to_rgba(LIGHTGRAY, .3))
        line_width = c.get_line_width()
        c.set_line_width(1)
        cx, cy = self.client.center

        for y in range(int((cy - 1080*self.screen_scale) / 50) * 50,
                       int(cy + 1080*self.screen_scale),
                       50):
            _, sy = self.world_to_screen_pos((0, y))
            c.move_to(0, sy)
            c.line_to(self.win_w, sy)
            c.stroke()

        for x in range(int((cx - 1920*self.screen_scale) / 50) * 50,
                       int(cx + 1920*self.screen_scale),
                       50):
            sx, _ = self.world_to_screen_pos((x, 0))
            c.move_to(sx, 0)
            c.line_to(sx, self.win_h)
            c.stroke()

        c.set_line_width(line_width)

        if self.show_debug:
            # world border
            wl, wt = self.world_to_screen_pos((0,0))
            c.set_source_rgba(*to_rgba(LIGHTGRAY, .5))
            c.rectangle(wl, wt, *(self.client.world_size*self.screen_scale,)*2)
            c.stroke()

        # cells
        # normal: show large over small, debug: show small over large
        for cell in sorted(self.client.cells.values(),
                key=lambda cell: cell.size, reverse=self.show_debug):
            x, y = self.world_to_screen_pos(pos_xy(cell))
            # circle
            c.set_source_rgba(*to_rgba(cell.color, .8))
            c.arc(x, y, cell.size * self.screen_scale, 0, TWOPI)
            c.fill()
            # name, size
            if cell.is_virus or cell.size < 20:  # food <= 11 < 30 <= cells
                pass  # do not draw name/size
            elif cell.is_agitated and self.show_debug:
                draw_text_center(c, (x, y), '(agitated)')
                draw_text_center(c, (x, y+12), '%i' % cell.size)
            elif cell.name:
                draw_text_center(c, (x, y), '%s' % cell.name)
                if self.show_debug:
                    draw_text_center(c, (x, y+12), '%i' % cell.size)
            elif self.show_debug:
                draw_text_center(c, (x, y), '%i' % cell.size)

        # draw handlers
        self.client.handle('draw', c=c, w=self)

        # leaderboard
        lb_x = self.win_w - self.LOG_W

        c.set_source_rgba(0,0,0, .6)
        c.rectangle(lb_x - 10, 0,
                    self.LOG_W, 21*len(self.client.leaderboard_names))
        c.fill()

        for i, (points, name) in enumerate(self.client.leaderboard_names):
            name = name or 'An unnamed cell'
            text = '%i. %s (%s)' % (i+1, name, points)
            draw_text_left(c, (lb_x, 20*(i+1)), text)

    def tick(self, drawing_area):
        self.client.handle('tick')
        drawing_area.queue_draw()
        return True

if __name__ == '__main__':
    print('Copyright (C) 2015  Gjum  <code.gjum@gmail.com>')
    print("This program comes with ABSOLUTELY NO WARRANTY.\n"
          "This is free software, and you are welcome to redistribute it\n"
          "under certain conditions; see LICENSE.txt for details.")
    AgarWindow()
