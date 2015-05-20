import random
from gi.repository import Gtk, GLib, Gdk
from client import AgarClient, Handler

special_names = 'poland;usa;china;russia;canada;australia;spain;brazil;' \
                'germany;ukraine;france;sweden;hitler;north korea;' \
                'south korea;japan;united kingdom;earth;greece;latvia;' \
                'lithuania;estonia;finland;norway;cia;maldivas;austria;' \
                'nigeria;reddit;yaranaika;confederate;9gag;indiana;4chan;' \
                'italy;ussr;bulgaria;tumblr;2ch.hk;hong kong;portugal;' \
                'jamaica;german empire;mexico;sanik;switzerland;croatia;' \
                'chile;indonesia;bangladesh;thailand;iran;iraq;peru;moon;' \
                'botswana;bosnia;netherlands;european union;taiwan;pakistan;' \
                'hungary;satanist;qing dynasty;nazi;matriarchy;patriarchy;' \
                'feminism;ireland;texas;facepunch;prodota;cambodia;steam;' \
                'piccolo;ea;india;kc;denmark;quebec;ayy lmao;sealand;bait;' \
                'tsarist russia;origin;vinesauce;stalin;belgium;luxembourg;' \
                'stussy;prussia;8ch;argentina;scotland;sir;romania;belarus;' \
                'wojak;isis;doge;nasa;byzantium;imperial japan;' \
                'french kingdom;somalia;turkey;mars;pokerface' \
    .split(';')

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
    x_bearing, y_bearing, text_width, text_height, x_advance, y_advance \
        = c.text_extents(text)
    cx, cy = center
    x = cx - x_bearing - text_width / 2
    y = cy - y_bearing - text_height / 2
    draw_text_left(c, (x, y), text, *args, **kwargs)

def draw_text_left(c, pos, text,
                   color=WHITE, shadow=None, size=12, face='sans'):
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

def pos_xy(o):
    return o.x, o.y

class LoggingHandler(Handler):

    def __init__(self, client):
        self.client = client
        self.log_msgs = []

    def log_msg(self, msg, update=9):
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
        url = self.client.url[5:-4]
        self.log_msg('Connected as "%s" to %s' % (self.client.nick, url))

    def on_cell_eaten(self, eater_id, eaten_id):
        if eaten_id in self.client.own_ids:
            name = 'Someone'
            if eater_id in self.client.cells:
                name = '"%s"' % self.client.cells[eater_id].name
            self.log_msg('%s ate me!' % name)

    def on_world_update_post(self):
        x, y = self.client.center
        px, py = x*100/self.client.world_size, y*100/self.client.world_size
        self.log_msg('Size: %i Pos: (%.2f %.2f) (%i%% %i%%)'
                     % (self.client.total_size, x, y, round(px), round(py)))

    def on_death(self):
        self.client.send_respawn()

    def on_own_id(self, cid):
        if len(self.client.own_ids) == 1:
            self.log_msg('Respawned', update=0)

class AgarWindow:
    LOG_W = 300

    def __init__(self):
        self.show_debug = False
        self.win_w, self.win_h = 1000, (1000-self.LOG_W) * 9/16
        self.map_w = self.win_w - self.LOG_W
        self.mouse_pos = 0,0
        self.screen_center = self.map_w / 2, self.win_h / 2
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

        self.logging_handler = LoggingHandler(self.client)
        self.client.add_handler(self.logging_handler)

        self.client.connect()
        self.logging_handler.log_msg('Press R to respawn', update=0)

        # check socket in GTK main loop
        GLib.io_add_watch(self.client.ws, GLib.IO_IN, lambda ws, _:
                          self.client.on_message(ws.recv()) or True)
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
        key = event.keyval
        if key == ord('q') or key == Gdk.KEY_Escape:
            self.client.disconnect()
            Gtk.main_quit()
        elif key == ord('h'):
            self.show_debug = not self.show_debug
        elif key == ord('r'):
            self.client.send_respawn()
        elif key == ord('w'):
            self.client.send_shoot()
        elif key == Gdk.KEY_space:
            self.client.send_split()

    def on_mouse_moved(self, _, event):
        self.mouse_pos = pos_xy(event)
        mouse_world = self.screen_to_world_pos(self.mouse_pos)
        self.client.send_mouse(*mouse_world)

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
        self.map_w = self.win_w - self.LOG_W
        self.screen_center = self.map_w / 2, self.win_h / 2

        self.screen_scale = self.client.scale * max(self.win_h / 1080, self.win_w / 1920)

        if self.show_debug:
            # world border
            wl, wt = self.world_to_screen_pos((0,0))
            c.set_source_rgba(*to_rgba(LIGHTGRAY, .5))
            c.rectangle(wl, wt, *(self.client.world_size*self.screen_scale,)*2)
            c.stroke()

            # movement lines
            for cid in self.client.own_ids:
                cell = self.client.cells[cid]
                x, y = self.world_to_screen_pos(pos_xy(cell))
                c.set_source_rgba(*to_rgba(FUCHSIA, .3))
                c.move_to(x,y)
                c.line_to(*self.mouse_pos)
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

        # logging area
        c.set_source_rgba(0,0,0, .6)
        c.rectangle(self.map_w,0, self.LOG_W, self.win_h)
        c.fill()

        infoarea_x = self.map_w + 10
        space_used = 0

        # leaderboard
        leader_line_h = 20
        for i, (points, name) in enumerate(self.client.leaderboard_names):
            name = name or 'An unnamed cell'
            text = '%i. %s (%s)' % (i+1, name, points)
            space_used += leader_line_h
            draw_text_left(c, (infoarea_x, space_used), text)
        space_used += leader_line_h

        # scrolling log
        log_line_h = 12
        log_char_w = 6  # seems to work with my font
        num_log_lines = int((self.win_h - space_used) / log_line_h)
        log = list(format_log(self.logging_handler.log_msgs,
                              self.LOG_W/log_char_w))
        for i, text in enumerate(log[-num_log_lines:]):
            draw_text_left(c, (infoarea_x, space_used),
                           text, size=10, face='monospace')
            space_used += log_line_h

    def tick(self, drawing_area):
        self.client.send_mouse(*self.screen_to_world_pos(self.mouse_pos))
        drawing_area.queue_draw()
        return True

if __name__ == '__main__':
    AgarWindow()
