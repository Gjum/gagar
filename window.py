from collections import defaultdict
# noinspection PyUnresolvedReferences
from gi.repository import Gtk, GLib
from client import AgarClient, get_url

TWOPI = 6.28

BLACK = (0,0,0)
WHITE = (1,1,1)
DARKGREY = (.2,.2,.2)
BLUE = (.2,.2,1)
FUCHSIA = (1,0,1)

BG_COLOR = DARKGREY

def to_rgba(c, a):
    return c[0], c[1], c[2], a

def scale_pos(pos, scale, view_center, screen_center):
    vx, vy = view_center
    sx, sy = screen_center
    x, y = pos
    x = (x-vx) * scale + sx
    y = (y-vy) * scale + sy
    return x, y

def draw_text(c, text, centerpos, color=WHITE, shadow=None):
    c.select_font_face('sans')
    c.set_font_size(12)
    x_bearing, y_bearing, text_width, text_height, x_advance, y_advance = c.text_extents(text)
    cx, cy = centerpos
    x = cx - x_bearing - text_width / 2
    y = cy - y_bearing - text_height / 2
    if shadow:
        s_color, s_offset = shadow
        s_dx, s_dy = s_offset
        c.move_to(x + s_dx, y + s_dy)
        c.set_source_rgba(*s_color)
        c.show_text(text)
    c.move_to(x, y)
    c.set_source_rgba(*color)
    c.show_text(text)

# noinspection PyAttributeOutsideInit
class Cell:
    def __init__(self, cid=-1, x=-1, y=-1, size=10, name='',
               color=BLACK, is_virus=False, is_agitated=False):
        self.cid = cid
        self.x = x
        self.y = y
        self.size = size
        self.name = name or None
        self.color = tuple(map(lambda rgb: rgb / 256.0, color))
        self.is_virus = is_virus
        self.is_agitated = is_agitated

        self.alpha = .8

    def update(self, cid=-1, x=-1, y=-1, size=10, name='',
               color=BLACK, is_virus=False, is_agitated=False):
        self.cid = cid
        self.x = x
        self.y = y
        self.size = size
        if name or self.name is None:
            self.name = name
        self.color = tuple(map(lambda rgb: rgb / 256.0, color))
        self.is_virus = is_virus
        self.is_agitated = is_agitated

        self.alpha = .8

    def tick(self):
        if self.name:
            self.alpha *= .9

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, pos_or_x, y=None):
        if y: pos_or_x = (pos_or_x, y)
        self.x, self.y = pos_or_x

    def draw(self, c, scale, view_center, screen_center):
        x, y = scale_pos(self.pos, scale, view_center, screen_center)
        c.set_source_rgba(*to_rgba(self.color, self.alpha))
        c.arc(x, y, self.size * scale, 0, TWOPI)
        c.fill()
        if self.alpha > .01:
            draw_text(c, self.name, (x, y))

def printer_for(text):
    def fun(**data):
        print(text, data)
    return fun

# noinspection PyAttributeOutsideInit
class AgarGame(AgarClient):

    def __init__(self):
        AgarClient.__init__(self)
        self.crash_on_errors = True
        self.add_handler('hello', lambda **data: self.send_handshake())
        self.add_handler('area', printer_for('Area'))
        self.add_handler('leaderboard_names', self.leaderboard_names)
        self.add_handler('cell_eaten', self.cell_eaten)
        self.add_handler('cell_info', self.cell_info)
        self.add_handler('cell_keep', self.cell_keep)

        # TODO init window
        self.reset_game()

    def reset_game(self):
        self.own_id = -1
        self.cells = defaultdict(Cell)

    def connect(self, url=None):
        url = url or get_url()
        socket = self.open_socket(url)
        print(url)

        GLib.io_add_watch(socket, GLib.IO_IN,
                          lambda _, __: self.on_message(self.ws.recv()) or True)
        GLib.io_add_watch(socket, GLib.IO_ERR,
                          lambda _, __: self.handle('error', error=None) or True)
        GLib.io_add_watch(socket, GLib.IO_HUP,
                          lambda _, __: self.on_close or True)

    def leaderboard_names(self, leaderboard):
        pass  # TODO

    def cell_eaten(self, a, b):
        pass  # TODO

    def cell_info(self, **kwargs):
        cid = kwargs['cid']
        self.cells[cid].update(**kwargs)

    def cell_keep(self, keep_cells):
        for cid, cell in self.cells.items():
            cell.tick()
            # if cid not in keep_cells:
            #     del self.cells[cid]

    def render(self, widget, c):
        c.set_source_rgba(*BG_COLOR)
        c.paint()

        scale = 700 / 11500.0 * 5
        view_center = [11180/2]*2
        screen_center = [700/2]*2

        for cell in self.cells.values():
            cell.draw(c, scale, view_center, screen_center)

game = AgarGame()
game.connect('ws://213.168.249.245:443')#get_url())

win = Gtk.Window()
win.set_title('agar.io')
win.set_default_size(700, 700)
win.connect('delete-event', Gtk.main_quit)

da=Gtk.DrawingArea()
da.connect('draw', game.render)
win.add(da)

GLib.timeout_add(50, lambda: da.queue_draw() or True)

win.show_all()
Gtk.main()
