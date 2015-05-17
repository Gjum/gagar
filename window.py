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

def format_log(lines, w, indent='  '):
    for l in lines:
        ind = ''
        while len(l) > len(ind):
            yield l[:w]
            ind = indent
            l = ind + l[w:]

def to_rgba(c, a):
    return c[0], c[1], c[2], a

def scale_pos(pos, scale, view_center, screen_center):
    vx, vy = view_center
    sx, sy = screen_center
    x, y = pos
    x = (x-vx) * scale + sx
    y = (y-vy) * scale + sy
    return x, y

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
        if self.name or self.is_agitated:
            self.alpha *= .8

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, pos_or_x, y=None):
        if y: pos_or_x = (pos_or_x, y)
        self.x, self.y = pos_or_x

    def draw(self, c, scale, view_center, screen_center):
        if self.alpha < .05:
            return
        x, y = scale_pos(self.pos, scale, view_center, screen_center)
        c.set_source_rgba(*to_rgba(self.color, self.alpha))
        c.arc(x, y, self.size * scale, 0, TWOPI)
        c.fill()
        draw_text_center(c, (x, y), self.name)

# noinspection PyAttributeOutsideInit
class AgarGame(AgarClient):

    def __init__(self, url):
        AgarClient.__init__(self)
        self.crash_on_errors = True
        self.add_handler('hello', lambda **data: self.send_handshake())
        self.add_handler('leaderboard_names', self.leaderboard_names)
        self.add_handler('cell_eaten', self.cell_eaten)
        self.add_handler('cell_info', self.cell_info)
        self.add_handler('cell_keep', self.cell_keep)

        self.add_handler('area', self.make_logger(
            'Area: from (%(left).2f, %(top).2f) to (%(right).2f, %(bottom).2f)'))
        self.add_handler('new_id', self.make_logger('New ID: %(cid)i'))
        self.add_handler('moved_wrongly', self.make_logger(
            'Moved Wrongly? [17] %s'))
        self.add_handler('20', self.make_logger('Reset? [20]'))

        self.own_id = -1
        self.cells = defaultdict(Cell)
        self.leaderboard = []
        self.log_msgs = []

        url = url or get_url()
        socket = self.open_socket(url)
        self.log_msgs.append('Connecting to %s' % url)

        GLib.io_add_watch(socket, GLib.IO_IN,
                          lambda _, __: self.on_message(self.ws.recv()) or True)
        GLib.io_add_watch(socket, GLib.IO_ERR,
                          lambda _, __: self.handle('error', error=None) or True)
        GLib.io_add_watch(socket, GLib.IO_HUP,
                          lambda _, __: self.on_close or True)

    def log_msg(self, msg):
        self.log_msgs.append(msg)
        print('[LOG]', msg)

    def make_logger(self, fmt):
        def fun(**data):
            try:
                text = fmt % data
            except TypeError:  # fmt is no formatting string
                text = '%s %s' % (fmt, data)
            self.log_msg(text)
        return fun

    def leaderboard_names(self, leaderboard):
        self.leaderboard = leaderboard

    def cell_eaten(self, a, b):
        pass  # TODO

    def cell_info(self, **kwargs):
        cid = kwargs['cid']
        self.cells[cid].update(**kwargs)

    def cell_keep(self, keep_cells):
        for cid, cell in self.cells.items():
            cell.tick()

    def render(self, widget, c):
        c.set_source_rgba(*BG_COLOR)
        c.paint()

        scale = WIN_W / WORLD_SIZE * 5
        view_center = WORLD_SIZE / 2, WORLD_SIZE / 2
        screen_center = WIN_W / 2, WIN_H / 2

        for cell in self.cells.values():
            cell.draw(c, scale, view_center, screen_center)

        c.set_source_rgba(0,0,0, .6)
        c.rectangle(WIN_W,0, LOG_W, WIN_H)
        c.fill()

        leader_x = WIN_W + 10

        # leaderboard
        leader_line_h = 20
        for i, (size, name) in enumerate(reversed(sorted(self.leaderboard))):
            i += 1  # start with 1, not 0
            text = '%i. %s (%s)' % (i, name, size)
            draw_text_left(c, (leader_x, leader_line_h*i), text)

        # scrolling log
        log_start_y = leader_line_h * (1 + len(self.leaderboard))
        log_line_h = 12
        num_log_lines = int((WIN_H - log_start_y) / log_line_h)
        self.log_msgs = self.log_msgs[-num_log_lines:]
        log = list(format_log(self.log_msgs, 47))[-num_log_lines:]
        for i, text in enumerate(log):
        # for i in range(30):
        #     text = '%02i ' % i
        #     text += ''.join('%i' % ((i+3)%10) for i in range(30))
            draw_text_left(c, (leader_x, log_start_y + log_line_h*i),
                           text, size=10, face='monospace')

WORLD_SIZE = 11180.339887498949  # TODO get from 'area' packet
LOG_W = 300
WIN_W = 800
WIN_H = 800*10/16

class AgarWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title('agar.io')
        self.set_default_size(WIN_W + LOG_W, WIN_H)
        self.connect('delete-event', Gtk.main_quit)

        game = AgarGame(get_url())

        da=Gtk.DrawingArea()
        da.connect('draw', game.render)
        self.add(da)

        GLib.timeout_add(50, lambda: da.queue_draw() or True)

        self.show_all()
        Gtk.main()

if __name__ == '__main__':
    AgarWindow()
