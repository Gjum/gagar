from collections import defaultdict
import struct
from sys import stderr
import websocket

WORLD_SIZE = 11180.339887498949  # when writing this, all maps had this size

class BufferUnderflowError(struct.error):
    def __init__(self, fmt, buf):
        self.fmt = fmt
        self.buf = buf
        self.args = ('Buffer too short: wanted %i %s, got %i %s'
                     % (struct.calcsize(fmt), fmt, len(buf), buf),)

class BufferStruct:
    def __init__(self, message):
        self.buffer = message

    def __str__(self):
        specials = {
            '\r': '\\r',
            '\n': '\\n',
            ' ': '␣',
        }
        nice_bytes = []
        hex_seen = False
        for b in self.buffer:
            if chr(b) in specials:
                if hex_seen:
                    nice_bytes.append(' ')
                    hex_seen = False
                nice_bytes.append(specials[chr(b)])
            elif 33 <= int(b) <= 126:  # printable
                if hex_seen:
                    nice_bytes.append(' ')
                    hex_seen = False
                nice_bytes.append('%c' % b)
            else:
                if not hex_seen:
                    nice_bytes.append(' 0x')
                    hex_seen = True
                nice_bytes.append('%02x' % b)
        return ''.join(nice_bytes)

    def pop_values(self, fmt):
        size = struct.calcsize(fmt)
        if len(self.buffer) < size:
            raise BufferUnderflowError(fmt, self.buffer)
        values = struct.unpack_from(fmt, self.buffer, 0)
        self.buffer = self.buffer[size:]
        return values

    def pop_uint8(self):
        return self.pop_values('<B')[0]

    def pop_uint16(self):
        return self.pop_values('<H')[0]

    def pop_uint32(self):
        return self.pop_values('<I')[0]

    def pop_float32(self):
        return self.pop_values('<f')[0]

    def pop_float64(self):
        return self.pop_values('<d')[0]

    def pop_str(self):
        l_name = []
        while 1:
            c = self.pop_uint16()
            if c == 0: break
            l_name.append(chr(c))
        return ''.join(l_name)

def get_url(region='EU-London'):
    import urllib.request
    addr = urllib.request.urlopen('http://m.agar.io', data=region.encode())\
            .read().decode().split('\n')[0]
    return 'ws://%s' % addr

class Handler:
    """Base class. `handle()` calls `self.on_<...>`."""

    def handle(self, ident, **data):
        func = getattr(self, 'on_%s' % ident, None)
        if func: func(**data)

class Cell:
    NO_COLOR = (1,0,1)

    def __init__(self):
        self.cid = -1
        self.x = -1
        self.y = -1
        self.size = -1
        self.name = ''
        self.color = Cell.NO_COLOR  # RGB tuple, channels are 0..1
        self.is_virus = False
        self.is_agitated = False

    def update(self, cid=-1, x=-1, y=-1, size=10, name='',
               color=NO_COLOR, is_virus=False, is_agitated=False):
        self.cid = cid
        self.x = x
        self.y = y
        self.size = size
        if name and not self.name:
            self.name = name
        self.color = tuple(map(lambda rgb: rgb / 256.0, color))
        self.is_virus = is_virus
        self.is_agitated = is_agitated

class AgarClient:
    """Talks to a server and maintains the world state."""

    packet_dict = {
        ord('H'): 'hello',
        16: 'world_update',
        32: 'own_id',
        49: 'leaderboard_names',
        50: 'leaderboard_groups',
        64: 'world_rect',
        17: '17', 20: '20',  # never sent by server, no idea what these are for
    }

    def __init__(self):
        self.handlers = []
        self.ws = websocket.WebSocket()
        self.url = ''
        self.cells = defaultdict(Cell)
        self.leaderboard_names = []
        self.leaderboard_groups = []
        self.own_ids = set()
        self.world_size = WORLD_SIZE  # size, not rect; assuming w == h
        self.nick = ''
        self.total_size = 0
        self.scale = 1
        self.center = self.world_size / 2, self.world_size / 2

    def add_handler(self, handler):
        self.handlers.append(handler)

    def remove_handler(self, handler):
        self.handlers.remove(handler)

    def handle(self, ident, **data):
        for handler in self.handlers[:]:
            try:
                handler.handle(ident, **data)
            except Exception as e:
                print('Handler %s failed on %s %s'
                      % (handler.__class__.__name__, ident, data),
                      file=stderr)
                raise e

    def connect(self, url=None):
        if self.ws.connected:
            raise ValueError('Already connected to "%s"', self.url)
        self.url = url or get_url()
        self.ws.connect(self.url, origin='http://agar.io')
        self.handle('sock_open')

    def disconnect(self):
        self.ws.close()
        self.reset_world()
        self.leaderboard_names = []
        self.leaderboard_groups = []

    def listen(self):
        """Set up a quick connection. Returns on disconnect."""
        import select
        while self.ws.connected:
            r, w, e = select.select((self.ws.sock, ), (), ())
            if r:
                self.on_message(self.ws.recv())
            elif e:
                self.handle('sock_error')
        self.handle('sock_closed')

    def reset_world(self):
        self.cells.clear()
        self.own_ids.clear()
        self.total_size = 0

    def on_message(self, msg):
        if not msg:
            print('ERROR empty message', file=stderr)
            return
        s = BufferStruct(msg)
        ident = self.packet_dict[s.pop_uint8()]
        parser = getattr(self, 'parse_%s' % ident, None)
        try:
            parser(s)
        except BufferUnderflowError as e:
            print('ERROR parsing', ident, 'packet failed:',
                  e.args[0], str(BufferStruct(msg)), file=stderr)
            raise e

    def parse_world_update(self, s):
        updated_cells = set()

        # we call handlers before changing any cells, so
        # handlers can print names, check own_ids, ...

        # ca eats cb
        for i in range(s.pop_uint16()):
            ca = s.pop_uint32()
            cb = s.pop_uint32()
            self.handle('cell_eaten', eater_id=ca, eaten_id=cb)
            if cb in self.own_ids:  # we got eaten
                if len(self.own_ids) <= 1:
                    self.handle('death')
                    # do not clear cells yet, they still get updated
                self.own_ids.remove(cb)
            if cb in self.cells:
                del self.cells[cb]
            updated_cells.add(ca)

        # create/update cells
        while 1:
            cid = s.pop_uint32()
            if cid == 0: break
            cx = s.pop_float32()
            cy = s.pop_float32()
            csize = s.pop_float32()
            color = (s.pop_uint8(), s.pop_uint8(), s.pop_uint8())
            bitmask = s.pop_uint8()
            is_virus = bool(bitmask & 1)
            is_agitated = bool(bitmask & 16)
            skips = 0  # lolwtf
            if bitmask & 2: skips += 4
            if bitmask & 4: skips += 8
            if bitmask & 8: skips += 16
            for i in range(skips): s.pop_uint8()
            cname = s.pop_str()
            self.handle('cell_info', cid=cid, x=cx, y=cy,
                        size=csize, name=cname, color=color,
                        is_virus=is_virus, is_agitated=is_agitated)
            self.cells[cid].update(cid=cid, x=cx, y=cy,
                        size=csize, name=cname, color=color,
                        is_virus=is_virus, is_agitated=is_agitated)
            self.handle('cell_updated', cid=cid)
            updated_cells.add(cid)

        s.pop_uint16()  # padding

        # also keep these non-updated cells
        for i in range(s.pop_uint32()):
            updated_cells.add(s.pop_uint32())

        # remove dead cells
        for cid in list(self.cells)[:]:
            if cid not in updated_cells:
                self.handle('cell_removed', cid=cid)
                del self.cells[cid]
                if cid in self.own_ids:  # own cells joined
                    self.own_ids.remove(cid)

        if self.own_ids:
            self.total_size = sum(self.cells[oid].size for oid in self.own_ids)
            self.scale = pow(min(1, 64 / self.total_size), 0.4)
        # else: keep current scale, also keep size for convenience

        if self.own_ids:
            left   = min(self.cells[cid].x for cid in self.own_ids)
            right  = max(self.cells[cid].x for cid in self.own_ids)
            top    = min(self.cells[cid].y for cid in self.own_ids)
            bottom = max(self.cells[cid].y for cid in self.own_ids)
            self.center = (left + right) / 2, (top + bottom) / 2

        self.handle('world_update_post')

    def parse_leaderboard_names(self, s):
        # sent every 500ms
        # only in "free for all" mode
        n = s.pop_uint32()
        leaderboard_names = []
        for i in range(n):
            l_id = s.pop_uint32()
            l_name = s.pop_str()
            leaderboard_names.append((l_id, l_name))
        self.handle('leaderboard_names', leaderboard=leaderboard_names)
        self.leaderboard_names = leaderboard_names

    def parse_leaderboard_groups(self, s):
        # sent every 500ms
        # only in group mode
        n = s.pop_uint32()
        leaderboard_groups = []
        for i in range(n):
            angle = s.pop_float32()
            leaderboard_groups.append(angle)
        self.handle('leaderboard_groups', angles=leaderboard_groups)
        self.leaderboard_groups = leaderboard_groups

    def parse_own_id(self, s):  # new cell ID, respawned or split
        cid = s.pop_uint32()
        if not self.own_ids:  # respawned
            self.reset_world()
        else:
            self.total_size = sum(self.cells[oid].size for oid in self.own_ids)
        self.cells[cid].name = self.nick
        self.own_ids.add(cid)
        self.handle('own_id', cid=cid)

    def parse_world_rect(self, s):  # world size
        left = s.pop_float64()
        top = s.pop_float64()
        right = s.pop_float64()
        bottom = s.pop_float64()
        # if the world was not square, we would have to change a lot
        assert right - left == bottom - top, 'World is not square'
        self.handle('world_rect', left=left, top=top, right=right, bottom=bottom)
        self.world_size = right - left

    def parse_hello(self, s):  # "HelloHelloHello", initial connection setup
        self.handle('hello')
        self.send_handshake()

    def parse_17(self, s):
        x = s.pop_float32()
        y = s.pop_float32()
        size = s.pop_float32()
        self.handle('17', x=x, y=y, size=size)

    def parse_20(self, s):
        self.handle('20')

    def send_struct(self, fmt, *data):
        if self.ws.connected:
            self.ws.send(struct.pack(fmt, *data))

    def send_handshake(self):
        self.send_struct('<BI', 255, 1)

    def send_respawn(self, nick=None):
        if nick is not None:
            self.nick = nick
        self.nick = str(self.nick)
        self.send_struct('<B%iH' % len(self.nick), 0, *map(ord, self.nick))

    def send_mouse(self, x, y):
        self.send_struct('<BddI', 16, x, y, 0)

    def send_spectate(self):
        self.send_struct('<B', 1)

    def send_split(self):
        self.send_struct('<B', 17)

    def send_shoot(self):
        self.send_struct('<B', 21)
