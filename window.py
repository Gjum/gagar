import random
from gi.repository import Gtk, GLib, Gdk
from client import AgarClient, get_url, WORLD_SIZE

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

BG_COLOR = DARKGRAY
BORDER_COLOR = LIGHTGRAY
CROSSHAIR_COLOR = to_rgba(FUCHSIA, .3)

def format_log(lines, w, indent='  '):
    w = int(w)
    for l in lines:
        ind = ''
        while len(l) > len(ind):
            yield l[:w]
            ind = indent
            l = ind + l[w:]

def world_to_screen_pos(pos, viewport):
    scale, world_center, screen_center = viewport
    vx, vy = world_center
    sx, sy = screen_center
    x, y = pos
    x = (x-vx) * scale + sx
    y = (y-vy) * scale + sy
    return x, y

def screen_to_world_pos(pos, viewport):
    # only works with current formula in world_to_screen_pos()
    scale, world_center, screen_center = viewport
    return world_to_screen_pos(pos, (1/scale, screen_center, world_center))

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

def draw_cell(c, cell, viewport, show_debug=False):
    x, y = world_to_screen_pos(pos_xy(cell), viewport)
    scale = viewport[0]
    # circle
    c.set_source_rgba(*to_rgba(cell.color, .8))
    c.arc(x, y, cell.size * scale, 0, TWOPI)
    c.fill()
    # name, size
    if cell.is_virus or cell.size < 20:  # food <= 11 < 30 <= cells
        pass  # do not draw name/size
    elif cell.is_agitated and show_debug:
        draw_text_center(c, (x, y), '(agitated)')
        draw_text_center(c, (x, y+12), '%i' % cell.size)
    elif cell.name:
        draw_text_center(c, (x, y), '%s' % cell.name)
        if show_debug: draw_text_center(c, (x, y+12), '%i' % cell.size)
    elif show_debug:
        draw_text_center(c, (x, y), '%i' % cell.size)

class AgarGame(AgarClient):

    def __init__(self, url, nick=None):
        AgarClient.__init__(self)
        self.log_msgs = []

        self.nick = random.choice(special_names) if nick is None else nick
        self.log_msg('Nick: %s' % self.nick)

        url = url or get_url()
        self.log_msg('Connecting to %s' % url)

        # check socket in GTK main loop
        socket = self.open_socket(url)
        GLib.io_add_watch(socket, GLib.IO_IN,
                          lambda ws, _: self.on_message(ws.recv()) or True)
        GLib.io_add_watch(socket, GLib.IO_ERR,
                          lambda _, __: self.handle('sock_error') or True)
        GLib.io_add_watch(socket, GLib.IO_HUP,
                          lambda _, __: self.handle('sock_closed') or True)

    def log_msg(self, msg, update=9):
        # update up to nineth-last msg with new data
        for i, log_msg in enumerate(reversed(
                self.log_msgs[-update:] if update else [])):
            if msg[:5] == log_msg[:5]:
                self.log_msgs[-i-1] = msg
                break
        else:
            self.log_msgs.append(msg)
            print('[LOG]', msg)

    def on_hello(self):
        self.send_handshake()
        self.log_msg('Press R to respawn', update=0)

    def on_cell_eaten(self, eater_id, eaten_id):
        if eaten_id in self.own_ids:  # we got eaten
            self.log_msg('"%s" ate me!' % (
                self.cells[eater_id].name or 'Someone'))
            if len(self.own_ids) <= 1:  # dead, restart
                self.send_restart()

    def on_world_update_post(self):
        if self.own_ids:
            size = sum(self.cells[oid].size for oid in self.own_ids)
            self.log_msg('Size: %i' % size)

    def on_own_id(self, cid):
        if len(self.own_ids) == 1:
            self.log_msg('Respawned', update=0)

# TODO auto-update on window resize
MAP_W = 800
LOG_W = 300
WIN_W = MAP_W+LOG_W
WIN_H = MAP_W*10/16

class AgarWindow:
    def __init__(self):
        # Gtk.main() swallows exceptions, get them back
        import sys
        sys.excepthook = lambda *a: sys.__excepthook__(*a) or sys.exit()

        self.game = None

        self.show_debug = False
        self.mouse_pos = 0,0
        self.screen_center = MAP_W / 2, WIN_H / 2
        self.scale = MAP_W / self.world_size * 5  # TODO calculate scale
        self.world_center = self.world_size / 2, self.world_size / 2

        self.window = Gtk.Window()
        self.window.set_title('agar.io')
        self.window.set_default_size(WIN_W, WIN_H)
        self.window.connect('delete-event', Gtk.main_quit)

        da = Gtk.DrawingArea()
        self.window.add(da)

        self.window.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.window.connect('key-press-event', self.on_key_pressed)
        self.window.connect('motion-notify-event', self.on_mouse_moved)
        da.connect('draw', self.draw)

        GLib.timeout_add(50, self.tick, da)
        GLib.idle_add(self.start_game)
        # TODO draw window before connecting

        Gtk.main()

    @property
    def world_size(self):
        # convenience function, do not crash when no game is running
        return self.game.world_size if self.game else WORLD_SIZE

    def start_game(self):
        self.game = AgarGame(get_url())
        self.window.show_all()

    def on_key_pressed(self, _, event):
        key = event.keyval
        if key == ord('q') or key == Gdk.KEY_Escape:
            if self.game:
                self.game.disconnect()
            Gtk.main_quit()
        elif key == ord('h'):
            self.show_debug = not self.show_debug
        elif self.game:
            if key == ord('r'):
                self.game.send_spectate()
                self.game.send_restart()
            elif key == ord('w'):
                self.game.send_shoot()
            elif key == Gdk.KEY_space:
                self.game.send_split()

    def on_mouse_moved(self, _, event):
        self.mouse_pos = pos_xy(event)
        mouse_world = screen_to_world_pos(self.mouse_pos, self.viewport)
        if self.game:
            self.game.send_mouse(*mouse_world)

    def update_viewport(self):
        if not self.game:
            return
        self.scale = MAP_W / self.game.world_size * 6  # TODO calculate scale
        if self.game.own_ids:
            left   = min(self.game.cells[cid].x for cid in self.game.own_ids)
            right  = max(self.game.cells[cid].x for cid in self.game.own_ids)
            top    = min(self.game.cells[cid].y for cid in self.game.own_ids)
            bottom = max(self.game.cells[cid].y for cid in self.game.own_ids)
            self.world_center = (left + right) / 2, (top + bottom) / 2

    @property
    def viewport(self):
        return self.scale, self.world_center, self.screen_center

    def draw(self, _, c):
        c.set_source_rgba(*BG_COLOR)
        c.paint()

        # draw game

        if not self.game:
            return

        self.update_viewport()

        if self.show_debug:
            # world border
            wl, wt = world_to_screen_pos((0,0), self.viewport)
            c.set_source_rgba(*BORDER_COLOR)
            c.rectangle(wl, wt, *(self.game.world_size*self.scale,)*2)
            c.stroke()

            # movement lines
            for cid in self.game.own_ids:
                cell = self.game.cells[cid]
                x, y = world_to_screen_pos(pos_xy(cell), self.viewport)
                c.set_source_rgba(*CROSSHAIR_COLOR)
                c.move_to(x,y)
                c.line_to(*self.mouse_pos)
                c.stroke()

        # cells
        for cell in self.game.cells.values():
            draw_cell(c, cell, self.viewport, show_debug=self.show_debug)

        # logging area
        c.set_source_rgba(0,0,0, .6)
        c.rectangle(MAP_W,0, LOG_W, WIN_H)
        c.fill()

        infoarea_x = MAP_W + 10
        space_used = 0

        # leaderboard
        leader_line_h = 20
        for i, (size, name) in enumerate(
                reversed(sorted(self.game.leaderboard_names))):
            text = '%i. %s (%s)' % (i+1, name, size)
            space_used += leader_line_h
            draw_text_left(c, (infoarea_x, space_used), text)
        space_used += leader_line_h

        # scrolling log
        log_line_h = 12
        log_char_w = 6  # seems to work with my font
        num_log_lines = int((WIN_H - space_used) / log_line_h)
        self.game.log_msgs = self.game.log_msgs[-num_log_lines:]
        log = list(format_log(self.game.log_msgs, LOG_W/log_char_w))
        for i, text in enumerate(log[-num_log_lines:]):
            draw_text_left(c, (infoarea_x, space_used),
                           text, size=10, face='monospace')
            space_used += log_line_h

    def tick(self, da):
        if self.game:
            self.game.send_mouse(
                *screen_to_world_pos(self.mouse_pos, self.viewport))
        da.queue_draw()
        return True

if __name__ == '__main__':
    AgarWindow()
