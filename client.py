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

from collections import defaultdict
import struct
from sys import stderr
import websocket
from buffer import BufferStruct, BufferUnderflowError

special_names = 'poland;usa;china;russia;canada;australia;spain;brazil;' \
                'germany;ukraine;france;sweden;hitler;north korea;' \
                'south korea;japan;united kingdom;earth;greece;latvia;' \
                'lithuania;estonia;finland;norway;cia;maldivas;austria;' \
                'nigeria;reddit;yaranaika;confederate;9gag;indiana;4chan;' \
                'italy;bulgaria;tumblr;2ch.hk;hong kong;portugal;' \
                'jamaica;german empire;mexico;sanik;switzerland;croatia;' \
                'chile;indonesia;bangladesh;thailand;iran;iraq;peru;moon;' \
                'botswana;bosnia;netherlands;european union;taiwan;pakistan;' \
                'hungary;satanist;qing dynasty;8;matriarchy;patriarchy;' \
                'feminism;ireland;texas;facepunch;prodota;cambodia;steam;' \
                'piccolo;ea;india;kc;denmark;quebec;ayy lmao;sealand;bait;' \
                'tsarist russia;origin;vinesauce;stalin;belgium;luxembourg;' \
                'stussy;prussia;8ch;argentina;scotland;sir;romania;belarus;' \
                'wojak;doge;nasa;byzantium;imperial japan;' \
                'french kingdom;somalia;turkey;mars;pokerface;' \
                'irs;receita federal' \
    .split(';')

WORLD_SIZE = 11180.339887498949  # when writing this, all maps had this size

def get_url(region='EU-London'):
    import urllib.request
    addr = urllib.request.urlopen('http://m.agar.io', data=region.encode())\
            .read().decode().split('\n')[0]
    return 'ws://%s' % addr

class Handler:
    """Base class. `handle()` calls `self.on_<...>`."""

    def __init__(self, client):
        self.client = client
        client.add_handler(self)

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

    @property
    def pos(self):
        return self.x, self.y

class AgarClient:
    """Talks to a server and maintains the world state."""

    packet_dict = {
        ord('H'): 'hello',
        16: 'world_update',
        32: 'own_id',
        49: 'leaderboard_names',
        50: 'leaderboard_groups',
        64: 'world_rect',
        17: 'pos_update',
        20: 'clear_cells',
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
            print('Already connected to "%s"', self.url, file=stderr)
            return False

        self.url = url or get_url()
        self.ws.connect(self.url, timeout=1, origin='http://agar.io')
        if not self.ws.connected:
            print('Failed to connect to "%s"', self.url, file=stderr)
            return False

        self.handle('sock_open')
        self.send_handshake()
        self.handle('ingame')
        return True

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
                self.on_message()
            elif e:
                self.handle('sock_error')
        self.handle('sock_closed')

    def reset_world(self):
        self.cells.clear()
        self.own_ids.clear()
        self.total_size = 0

    def on_message(self):
        try:
            msg = self.ws.recv()
        except Exception:
            self.disconnect()
            return
        if not msg:
            print('ERROR empty message', file=stderr)
            return
        buf = BufferStruct(msg)
        ident = self.packet_dict[buf.pop_uint8()]
        parser = getattr(self, 'parse_%s' % ident, None)
        try:
            parser(buf)
        except BufferUnderflowError as e:
            print('ERROR parsing', ident, 'packet failed:',
                  e.args[0], str(BufferStruct(msg)), file=stderr)
            raise e

    def parse_world_update(self, buf):
        # we call handlers before changing any cells, so
        # handlers can print names, check own_ids, ...

        # ca eats cb
        for i in range(buf.pop_uint16()):
            ca = buf.pop_uint32()
            cb = buf.pop_uint32()
            self.handle('cell_eaten', eater_id=ca, eaten_id=cb)
            if cb in self.own_ids:  # we got eaten
                if len(self.own_ids) <= 1:
                    self.handle('death')
                    # do not clear cells yet, they still get updated
                self.own_ids.remove(cb)
            if cb in self.cells:
                self.handle('cell_removed', cid=cb)
                del self.cells[cb]

        # create/update cells
        while 1:
            cid = buf.pop_uint32()
            if cid == 0: break
            cx = buf.pop_uint16()
            cy = buf.pop_uint16()
            csize = buf.pop_uint16()
            color = (buf.pop_uint8(), buf.pop_uint8(), buf.pop_uint8())
            bitmask = buf.pop_uint8()
            is_virus = bool(bitmask & 1)
            is_agitated = bool(bitmask & 16)
            skips = 0  # lolwtf
            if bitmask & 2: skips += 4
            if bitmask & 4: skips += 8
            if bitmask & 8: skips += 16
            for i in range(skips): buf.pop_uint8()
            cname = buf.pop_str()
            self.handle('cell_info', cid=cid, x=cx, y=cy,
                        size=csize, name=cname, color=color,
                        is_virus=is_virus, is_agitated=is_agitated)
            self.cells[cid].update(cid=cid, x=cx, y=cy,
                        size=csize, name=cname, color=color,
                        is_virus=is_virus, is_agitated=is_agitated)
            self.handle('cell_updated', cid=cid)

        # also keep these non-updated cells
        for i in range(buf.pop_uint32()):
            cid = buf.pop_uint32()
            if cid in self.cells:
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

    def parse_leaderboard_names(self, buf):
        # sent every 500ms
        # only in "free for all" mode
        n = buf.pop_uint32()
        leaderboard_names = []
        for i in range(n):
            l_id = buf.pop_uint32()
            l_name = buf.pop_str()
            leaderboard_names.append((l_id, l_name))
        self.handle('leaderboard_names', leaderboard=leaderboard_names)
        self.leaderboard_names = leaderboard_names

    def parse_leaderboard_groups(self, buf):
        # sent every 500ms
        # only in group mode
        n = buf.pop_uint32()
        leaderboard_groups = []
        for i in range(n):
            angle = buf.pop_float32()
            leaderboard_groups.append(angle)
        self.handle('leaderboard_groups', angles=leaderboard_groups)
        self.leaderboard_groups = leaderboard_groups

    def parse_own_id(self, buf):  # new cell ID, respawned or split
        cid = buf.pop_uint32()
        if not self.own_ids:  # respawned
            self.reset_world()
        else:
            self.total_size = sum(self.cells[oid].size for oid in self.own_ids)
        self.cells[cid].name = self.nick
        self.own_ids.add(cid)
        self.handle('own_id', cid=cid)

    def parse_world_rect(self, buf):  # world size
        left = buf.pop_float64()
        top = buf.pop_float64()
        right = buf.pop_float64()
        bottom = buf.pop_float64()
        # if the world was not square, we would have to change a lot
        assert right - left == bottom - top, 'World is not square'
        self.handle('world_rect', left=left, top=top, right=right, bottom=bottom)
        self.world_size = right - left

    def parse_pos_update(self, buf):
        x = buf.pop_float32()
        y = buf.pop_float32()
        size = self.total_size = buf.pop_float32()
        self.center = x, y
        self.scale = pow(min(1, 64 / size), 0.4)
        self.handle('pos_update', x=x, y=y, size=size)

    def parse_clear_cells(self, buf):
        self.handle('clear_cells')
        self.cells.clear()

    def send_struct(self, fmt, *data):
        if self.ws.connected:
            self.ws.send(struct.pack(fmt, *data))

    def send_handshake(self):
        self.send_struct('<BI', 254, 4)
        self.send_struct('<BI', 255, 673720360)

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
