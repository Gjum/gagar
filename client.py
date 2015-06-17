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
from event import Channel
from vec import Vec


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


def get_url(region='EU-London'):
    import urllib.request
    addr = urllib.request.urlopen('http://m.agar.io', data=region.encode())\
            .read().decode().split('\n')[0]
    return 'ws://%s' % addr


class Cell(object):
    def __init__(self, cid=-1, x=0, y=0, size=0, name='',
                 color=(1, 0, 1), is_virus=False, is_agitated=False):
        self.cid = cid
        self.pos = Vec(x, y)
        self.size = size
        self.name = getattr(self, 'name', name) or name
        self.color = tuple(map(lambda rgb: rgb / 255.0, color))
        self.is_virus = is_virus
        self.is_agitated = is_agitated

    def same_player(self, other):
        """
        Compares name and color.
        Returns True if both are owned by the same player.
        """
        return self.name == other.name \
                and self.color == other.color

    def __lt__(self, other):
        if self.size != other.size:
            return self.size < other.size
        return self.cid < other.cid


class World(object):
    def __init__(self):
        self.cells = defaultdict(Cell)
        self.leaderboard_names = []
        self.leaderboard_groups = []
        self.size = Vec(0, 0)

    def __eq__(self, other):
        """Compare two worlds by comparing their leaderboards."""
        for ls, lo in zip(self.leaderboard_names, other.leaderboard_names):
            if ls != lo:
                return False
        for ls, lo in zip(self.leaderboard_groups, other.leaderboard_groups):
            if ls != lo:
                return False
        return True


class Player(object):
    def __init__(self):
        self.world = World()
        self.own_ids = set()
        self.nick = ''
        self.center = self.world.size / 2
        self.last_scale = 1

    def reset(self):
        # xxx
        self.own_ids.clear()

    @property
    def own_cells(self):
        cells = self.world.cells
        return map(lambda cid: cells[cid], self.own_ids)

    @property
    def total_size(self):
        return sum(cell.size for cell in self.own_cells)

    @property
    def scale(self):
        if self.is_alive:
            self.last_scale = pow(min(1, 64 / self.total_size), 0.4)
        return self.last_scale

    @property
    def is_alive(self):
        return bool(self.own_ids)

    @property
    def is_spectating(self):
        return not self.is_alive

    # @property
    # def visible_area(self):
    #     """Calculated like in the vanilla client."""
    #     raise NotImplementedError
    #     return Vec(), Vec()


class Client(object):
    """Talks to a server and calls handlers on events."""

    packet_dict = {
        16: 'world_update',
        17: 'spectate_update',
        20: 'clear_cells',
        32: 'own_id',
        49: 'leaderboard_names',
        50: 'leaderboard_groups',
        64: 'world_rect',
    }

    def __init__(self, channel=Channel()):
        self.channel = channel
        self.player = Player()
        self.world = self.player.world
        self.ws = websocket.WebSocket()
        self.url = ''

    def connect(self, url=None):
        if self.ws.connected:
            print('Already connected to "%s"', self.url, file=stderr)
            return False

        self.url = url or get_url()
        self.ws.connect(self.url, timeout=1, origin='http://agar.io')
        if not self.ws.connected:
            print('Failed to connect to "%s"', self.url, file=stderr)
            return False

        self.channel.broadcast('sock_open')
        # allow handshake canceling
        if not self.ws.connected:
            print('Disconnected before sending handshake', file=stderr)
            return False

        self.send_handshake()
        self.player.world = self.world = World()
        self.channel.broadcast('ingame')
        return True

    def disconnect(self):
        self.ws.close()
        self.channel.broadcast('sock_closed')
        self.player.reset()

    def listen(self):
        """Set up a quick connection. Returns on disconnect."""
        import select
        while self.ws.connected:
            r, w, e = select.select((self.ws.sock, ), (), ())
            if r:
                self.on_message()
            elif e:
                self.channel.broadcast('sock_error')
        self.disconnect()

    def on_message(self):
        try:
            msg = self.ws.recv()
        except Exception:
            self.disconnect()
            return
        if not msg:
            print('ERROR empty message received', file=stderr)
            return
        buf = BufferStruct(msg)
        ident = self.packet_dict[buf.pop_uint8()]
        parser = getattr(self, 'parse_%s' % ident)
        try:
            parser(buf)
            assert len(buf.buffer) == 0, \
                'Buffer not empty after parsing "%s" packet' % ident
        except BufferUnderflowError as e:
            print('ERROR parsing', ident, 'packet failed:',
                  e.args[0], str(BufferStruct(msg)), file=stderr)
            raise e

    def parse_world_update(self, buf):
        # we keep the previous world state, so
        # handlers can print names, check own_ids, ...

        player = self.player
        cells = self.world.cells

        # ca eats cb
        for i in range(buf.pop_uint16()):
            ca = buf.pop_uint32()
            cb = buf.pop_uint32()
            self.channel.broadcast('cell_eaten', eater_id=ca, eaten_id=cb)
            if cb in self.player.own_ids:  # we got eaten
                if len(self.player.own_ids) <= 1:
                    self.channel.broadcast('death')
                    # do not clear all cells yet, they still get updated
                self.player.own_ids.remove(cb)
            if cb in cells:
                self.channel.broadcast('cell_removed', cid=cb)
                del cells[cb]

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
            self.channel.broadcast('cell_info', cid=cid, x=cx, y=cy,
                                   size=csize, name=cname, color=color,
                                   is_virus=is_virus, is_agitated=is_agitated)
            cells[cid].__init__(cid=cid, x=cx, y=cy,
                                size=csize, name=cname, color=color,
                                is_virus=is_virus, is_agitated=is_agitated)

        # also keep these non-updated cells
        for i in range(buf.pop_uint32()):
            cid = buf.pop_uint32()
            if cid in cells:
                self.channel.broadcast('cell_removed', cid=cid)
                del cells[cid]
                if cid in player.own_ids:  # own cells joined
                    player.own_ids.remove(cid)

        own_cells = list(player.own_cells)
        if own_cells:
            left   = min(cell.pos.x for cell in own_cells)
            right  = max(cell.pos.x for cell in own_cells)
            top    = min(cell.pos.y for cell in own_cells)
            bottom = max(cell.pos.y for cell in own_cells)
            player.center = Vec(left + right, top + bottom) / 2

        self.channel.broadcast('world_update_post')

    def parse_leaderboard_names(self, buf):
        # sent every 500ms
        # only in "free for all" mode
        n = buf.pop_uint32()
        leaderboard_names = []
        for i in range(n):
            l_id = buf.pop_uint32()
            l_name = buf.pop_str()
            leaderboard_names.append((l_id, l_name))
        self.channel.broadcast('leaderboard_names', leaderboard=leaderboard_names)
        self.world.leaderboard_names = leaderboard_names

    def parse_leaderboard_groups(self, buf):
        # sent every 500ms
        # only in group mode
        n = buf.pop_uint32()
        leaderboard_groups = []
        for i in range(n):
            angle = buf.pop_float32()
            leaderboard_groups.append(angle)
        self.channel.broadcast('leaderboard_groups', angles=leaderboard_groups)
        self.world.leaderboard_groups = leaderboard_groups

    def parse_own_id(self, buf):  # new cell ID, respawned or split
        cid = buf.pop_uint32()
        player = self.player
        if not player.own_ids:  # respawned
            player.reset()
        # server sends empty name, assumes we set it here
        self.world.cells[cid].name = player.nick
        player.own_ids.add(cid)
        self.channel.broadcast('own_id', cid=cid)

    def parse_world_rect(self, buf):  # world size
        left = buf.pop_float64()
        top = buf.pop_float64()
        right = buf.pop_float64()
        bottom = buf.pop_float64()
        assert int(right - left) == int(bottom - top) == 11180, 'World is not expected size'  # xxx
        self.channel.broadcast('world_rect',
                               left=left, top=top, right=right, bottom=bottom)
        self.world.size.set(right - left, bottom - top)
        self.player.center = self.world.size / 2

    def parse_spectate_update(self, buf):
        # only in spectate mode
        x = buf.pop_float32()
        y = buf.pop_float32()
        scale = buf.pop_float32()
        self.player.center.set(x, y)
        self.player.last_scale = scale
        self.channel.broadcast('spectate_update',
                               pos=self.player.center, scale=scale)

    def parse_clear_cells(self, buf):
        # TODO clear cells packet is untested
        self.channel.broadcast('clear_cells')
        self.player.own_ids.clear()
        self.world.cells.clear()

    def send_struct(self, fmt, *data):
        if self.ws.connected:
            self.ws.send(struct.pack(fmt, *data))

    def send_handshake(self):
        self.send_struct('<BI', 254, 4)
        self.send_struct('<BI', 255, 673720360)

    def send_respawn(self):
        nick = self.player.nick
        self.send_struct('<B%iH' % len(nick), 0, *map(ord, nick))

    def send_mouse(self, x, y):
        self.send_struct('<BddI', 16, x, y, 0)

    def send_spectate(self):
        self.send_struct('<B', 1)

    def send_split(self):
        self.send_struct('<B', 17)

    def send_shoot(self):
        self.send_struct('<B', 21)
