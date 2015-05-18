from collections import defaultdict
import random
# noinspection PyUnresolvedReferences
from gi.repository import Gtk, GLib, Gdk
from client import AgarClient, get_url

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

def world_to_screen_pos(pos, scale, world_center, screen_center):
    vx, vy = world_center
    sx, sy = screen_center
    x, y = pos
    x = (x-vx) * scale + sx
    y = (y-vy) * scale + sy
    return x, y

def screen_to_world_pos(pos, scale, world_center, screen_center):
    # only works with current formula in world_to_screen_pos()
    return world_to_screen_pos(pos, 1/scale, screen_center, world_center)

def draw_text_center(c, center, text, *args, **kwargs):
    x_bearing, y_bearing, text_width, text_height, x_advance, y_advance = c.text_extents(text)
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

class Cell:
    def __init__(self):
        self.cid = -1
        self.x = -1
        self.y = -1
        self.size = -1
        self.name = ''
        self.color = FUCHSIA
        self.is_virus = False
        self.is_agitated = False

    def update(self, cid=-1, x=-1, y=-1, size=10, name='',
               color=BLACK, is_virus=False, is_agitated=False):
        self.cid = cid
        self.x = x
        self.y = y
        self.size = size
        if name and not self.name:
            self.name = name
        self.color = tuple(map(lambda rgb: rgb / 256.0, color))
        self.is_virus = is_virus
        self.is_agitated = is_agitated

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, pos_or_x, y=None):
        if y: pos_or_x = (pos_or_x, y)
        self.x, self.y = pos_or_x

    def draw(self, c, scale, view_center, screen_center, show_debug=False):
        x, y = world_to_screen_pos(self.pos, scale, view_center, screen_center)
        # circle
        c.set_source_rgba(*to_rgba(self.color, .8))
        c.arc(x, y, self.size * scale, 0, TWOPI)
        c.fill()
        # name, size
        if self.is_virus or self.size < 20:  # food <= 11 < 30 <= cells
            pass  # do not draw name/size
        elif self.is_agitated and show_debug:
            draw_text_center(c, (x, y), '(agitated)')
            draw_text_center(c, (x, y+12), '%i' % self.size)
        elif self.name:
            draw_text_center(c, (x, y), '%s' % self.name)
            if show_debug: draw_text_center(c, (x, y+12), '%i' % self.size)
        elif show_debug:
            draw_text_center(c, (x, y), '%i' % self.size)

def make_logger(fmt):
    def fun(**data):
        try:
            text = fmt % data
        except TypeError:  # fmt is no formatting string
            text = '%s %s' % (fmt, data)
        print('[LOG]', text)
    return fun

class AgarGame(AgarClient):

    def __init__(self, url):
        AgarClient.__init__(self)
        self.crash_on_errors = True
        self.add_handler('hello', self.on_hello)
        self.add_handler('leaderboard_names', self.on_leaderboard_names)
        self.add_handler('cell_eaten', self.on_cell_eaten)
        self.add_handler('cell_info', self.on_cell_info)
        self.add_handler('cell_keep', self.on_cell_keep)
        self.add_handler('new_id', self.on_new_id)
        self.add_handler('area', self.on_area)

        self.add_handler('moved_wrongly', make_logger('Moved Wrongly? [17] %s'))
        self.add_handler('20', make_logger('Reset? [20]'))

        # reset_world
        self.own_ids = set()
        self.cells = defaultdict(Cell)

        self.updated_cells = set()
        self.leaderboard = []
        self.world_size = 11180.339887498949
        self.log_msgs = []
        self.show_debug = False

        self.mouse_pos = 0,0
        self.screen_center = MAP_W / 2, WIN_H / 2
        # update_view
        self.scale = MAP_W / self.world_size * 5  # TODO calculate scale
        self.world_center = self.world_size / 2, self.world_size / 2

        url = url or get_url()
        socket = self.open_socket(url)
        self.log_msg('Connecting to %s' % url)

        GLib.io_add_watch(socket, GLib.IO_IN,
                          lambda _, __: self.on_message(self.ws.recv()) or True)
        GLib.io_add_watch(socket, GLib.IO_ERR,
                          lambda _, __: self.handle('error', error=None) or True)
        GLib.io_add_watch(socket, GLib.IO_HUP,
                          lambda _, __: self.on_close or True)

        self.nick = random.choice(special_names)

    def on_hello(self, **_):
        self.send_handshake()
        self.nick = random.choice(special_names)
        self.log_msg('Nick: %s' % self.nick)
        self.log_msg('Press R to start the game', update=0)

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

    def on_leaderboard_names(self, leaderboard):
        self.leaderboard = leaderboard

    def on_cell_eaten(self, a, b):
        if b in self.own_ids:  # we got eaten
            self.log_msg('"%s" ate me!' % self.cells[a].name or 'Someone')
            self.own_ids.remove(b)
            if not self.own_ids:  # dead, restart
                self.send_nick(self.nick)

        if b in self.cells:
            del self.cells[b]

    def on_cell_info(self, **kwargs):
        cid = kwargs['cid']
        self.cells[cid].update(**kwargs)
        self.updated_cells.add(cid)
        if cid in self.own_ids:
            size = sum(self.cells[oid].size for oid in self.own_ids)
            self.log_msg('Size: %i' % size)

    def on_cell_keep(self, keep_cells):
        self.updated_cells.update(keep_cells)
        # remove dead cells
        for cid in list(self.cells)[:]:
            if cid not in self.updated_cells:
                del self.cells[cid]
                if cid in self.own_ids:  # own cells joined
                    self.own_ids.remove(cid)
        self.updated_cells.clear()

    def on_new_id(self, cid):
        if not self.own_ids:
            self.log_msg('Respawned', update=0)
            self.cells = defaultdict(Cell)
            self.own_ids.clear()
        self.own_ids.add(cid)
        self.cells[cid].name = self.nick

    def on_area(self, left, top, right, bottom):
        assert right - left == bottom - top, 'World is not square'
        self.world_size = right - left
        self.log_msg('Area: from (%.2f, %.2f) to (%.2f, %.2f)' \
                     % (left, top, right, bottom))

    def on_key_pressed(self, widget, event):
        key = event.keyval
        if key == ord('h'):
            self.show_debug = not self.show_debug
        elif key == ord('r'):
            self.send_spectate()
            self.send_nick(self.nick)
        elif key == ord('w'):
            self.send_shoot()
        elif key == Gdk.KEY_space:
            self.send_split()
        elif key == ord('q') or key == Gdk.KEY_Escape:
            self.disconnect()
            Gtk.main_quit()

    def on_mouse_moved(self, widget, event):
        self.mouse_pos = x, y = event.x, event.y
        mouse_world = screen_to_world_pos((x, y), *self.view_params)
        self.send_mouse(*mouse_world)

    def update_view(self):
        self.scale = MAP_W / self.world_size * 6  # TODO calculate scale
        if self.own_ids:
            left   = min(self.cells[cid].x for cid in self.own_ids)
            right  = max(self.cells[cid].x for cid in self.own_ids)
            top    = min(self.cells[cid].y for cid in self.own_ids)
            bottom = max(self.cells[cid].y for cid in self.own_ids)
            self.world_center = (right + left) / 2, (bottom + top) / 2

    @property
    def view_params(self):
        return self.scale, self.world_center, self.screen_center

    def render(self, widget, c):
        c.set_source_rgba(*BG_COLOR)
        c.paint()

        self.update_view()

        if self.show_debug:
            # world border
            wl, wt = world_to_screen_pos((0,0), *self.view_params)
            c.set_source_rgba(*BORDER_COLOR)
            c.rectangle(wl, wt, *(self.world_size*self.scale,)*2)
            c.stroke()

            # movement lines
            for cid in self.own_ids:
                cell = self.cells[cid]
                x, y = world_to_screen_pos((cell.x, cell.y), *self.view_params)
                c.set_source_rgba(*CROSSHAIR_COLOR)
                c.move_to(x,y)
                c.line_to(*self.mouse_pos)
                c.stroke()

        # cells
        for cell in self.cells.values():
            cell.draw(c, *self.view_params, show_debug=self.show_debug)

        # logging area
        c.set_source_rgba(0,0,0, .6)
        c.rectangle(MAP_W,0, LOG_W, WIN_H)
        c.fill()

        infoarea_x = MAP_W + 10
        space_used = 0

        # leaderboard
        leader_line_h = 20
        for i, (size, name) in enumerate(reversed(sorted(self.leaderboard))):
            text = '%i. %s (%s)' % (i+1, name, size)
            space_used += leader_line_h
            draw_text_left(c, (infoarea_x, space_used), text)
        space_used += leader_line_h

        # scrolling log
        log_line_h = 12
        log_char_w = 6  # xxx
        num_log_lines = int((WIN_H - space_used) / log_line_h)
        self.log_msgs = self.log_msgs[-num_log_lines:]
        log = list(format_log(self.log_msgs, LOG_W/log_char_w))
        for i, text in enumerate(log[-num_log_lines:]):
            draw_text_left(c, (infoarea_x, space_used),
                           text, size=10, face='monospace')
            space_used += log_line_h

    def tick(self, da):
        self.send_mouse(*screen_to_world_pos(self.mouse_pos, *self.view_params))
        da.queue_draw()

        return True

MAP_W = 800
LOG_W = 300
WIN_W = MAP_W+LOG_W
WIN_H = MAP_W*10/16

class AgarWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title('agar.io')
        self.set_default_size(WIN_W, WIN_H)
        self.connect('delete-event', Gtk.main_quit)

        game = AgarGame(get_url())

        da=Gtk.DrawingArea()
        self.add(da)

        self.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('key-press-event', game.on_key_pressed)
        self.connect('motion-notify-event', game.on_mouse_moved)
        da.connect('draw', game.render)

        GLib.timeout_add(50, game.tick, da)

        # Gtk.main() swallows exceptions, get them back
        import sys
        sys.excepthook = lambda *a: sys.__excepthook__(*a) or sys.exit()

        self.show_all()
        Gtk.main()

if __name__ == '__main__':
    AgarWindow()
