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

import struct
import websocket

from .buffer import BufferStruct, BufferUnderflowError
from .vec import Vec
from .world import Player

packet_s2c = {
    16: 'world_update',
    17: 'spectate_update',
    20: 'clear_cells',
    21: 'debug_line',
    32: 'own_id',
    49: 'leaderboard_names',
    50: 'leaderboard_groups',
    64: 'world_rect',
}

packet_c2s = {
      0: 'respawn',
      1: 'spectate',
     16: 'mouse',
     17: 'split',
     18: 'shoot',
     20: 'explode',
     80: 'token',
    254: 'handshake1',
    255: 'handshake2',
}

ingame_packets = ('world_rect', 'world_update', 'leaderboard_names',
                  'leaderboard_groups', 'spectate_update', 'own_id')

moz_headers = [
    ('User-Agent', 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'),
    ('Origin', 'http://agar.io'),
    ('Referer', 'http://agar.io'),
]


handshake_version = 154669603


class Client(object):
    """Talks to a server and calls handlers on events."""

    def __init__(self, subscriber):
        """
        :param subscriber: instance of a subclass of Subscriber, i.e. imlements any on_*() methods
        """
        self.subscriber = subscriber
        self.player = Player()
        self.ws = websocket.WebSocket()
        self.address = ''
        self.token = ''
        self.ingame = False

    @property
    def world(self):
        return self.player.world

    @world.setter
    def world(self, world):
        self.player.world = world

    @property
    def is_connected(self):
        return self.ws.connected

    def connect(self, address, token=None):
        """
        Connect the underlying websocket to the address, send a handshake and optionally a token packet.

        :param address: string, `IP:PORT`
        :param token: unique token, required by official servers, acquired through find_server()
        :return: True if connected, False if not
        """
        if self.is_connected:
            self.subscriber.on_log_msg('Already connected to "%s"' % self.address)
            return False

        self.address, self.token = address, token
        self.ingame = False
        self.ws.connect('ws://%s' % self.address, timeout=1, origin='http://agar.io',
                        header=[': '.join(h)for h in moz_headers])
        if not self.is_connected:
            self.subscriber.on_log_msg('Failed to connect to "%s"' % self.address)
            return False

        self.subscriber.on_sock_open()
        # allow handshake canceling
        if not self.is_connected:
            self.subscriber.on_log_msg('Disconnected before sending handshake')
            return False

        self.send_handshake()
        if self.token:
            self.send_token(self.token)

        old_nick = self.player.nick
        self.player = Player()
        self.player.nick = old_nick
        return True

    def disconnect(self):
        self.ws.close()
        self.ingame = False
        self.subscriber.on_sock_closed()
        # keep player/world data

    def listen(self):
        """Set up a quick connection. Returns on disconnect."""
        import select
        while self.is_connected:
            r, w, e = select.select((self.ws.sock, ), (), ())
            if r:
                self.on_message()
            elif e:
                self.subscriber.on_sock_error()
        self.disconnect()

    def on_message(self):
        try:
            msg = self.ws.recv()
        except Exception:
            self.disconnect()
            return
        if not msg:
            self.subscriber.on_log_msg('ERROR empty message received')
            return
        buf = BufferStruct(msg)
        opcode = buf.pop_uint8()
        try:
            packet_name = packet_s2c[opcode]
        except KeyError:
            self.subscriber.on_log_msg('ERROR unknown packet %s' % opcode)
            return
        if not self.ingame and packet_name in ingame_packets:
            self.subscriber.on_ingame()
            self.ingame = True
        parser = getattr(self, 'parse_%s' % packet_name)
        try:
            parser(buf)
            assert len(buf.buffer) == 0, \
                'Buffer not empty after parsing "%s" packet' % packet_name
        except BufferUnderflowError as e:
            msg = 'ERROR parsing %s packet failed: %s' % (packet_name, e.args[0])
            self.subscriber.on_log_msg(msg)
            raise e

    def parse_world_update(self, buf):
        self.subscriber.on_world_update_pre()

        # we keep the previous world state, so
        # handlers can print names, check own_ids, ...

        cells = self.player.world.cells

        # ca eats cb
        for i in range(buf.pop_uint16()):
            ca = buf.pop_uint32()
            cb = buf.pop_uint32()
            self.subscriber.on_cell_eaten(eater_id=ca, eaten_id=cb)
            if cb in self.player.own_ids:  # we got eaten
                if len(self.player.own_ids) <= 1:
                    self.subscriber.on_death()
                    # do not clear all cells yet, they still get updated
                self.player.own_ids.remove(cb)
            if cb in cells:
                self.subscriber.on_cell_removed(cid=cb)
                del cells[cb]

        # create/update cells
        while 1:
            cid = buf.pop_uint32()
            if cid == 0: break
            cx = buf.pop_int32()
            cy = buf.pop_int32()
            csize = buf.pop_int16()
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
            self.subscriber.on_cell_info(cid=cid, x=cx, y=cy,
                                         size=csize, name=cname, color=color,
                                         is_virus=is_virus, is_agitated=is_agitated)
            cells[cid].__init__(cid=cid, x=cx, y=cy,
                                size=csize, name=cname, color=color,
                                is_virus=is_virus, is_agitated=is_agitated)

        # also keep these non-updated cells
        for i in range(buf.pop_uint32()):
            cid = buf.pop_uint32()
            if cid in cells:
                self.subscriber.on_cell_removed(cid=cid)
                del cells[cid]
                if cid in self.player.own_ids:  # own cells joined
                    self.player.own_ids.remove(cid)

        self.player.cells_changed()

        self.subscriber.on_world_update_post()

    def parse_leaderboard_names(self, buf):
        # sent every 500ms
        # only in "free for all" mode
        n = buf.pop_uint32()
        leaderboard_names = []
        for i in range(n):
            l_id = buf.pop_uint32()
            l_name = buf.pop_str()
            leaderboard_names.append((l_id, l_name))
        self.subscriber.on_leaderboard_names(leaderboard=leaderboard_names)
        self.player.world.leaderboard_names = leaderboard_names

    def parse_leaderboard_groups(self, buf):
        # sent every 500ms
        # only in group mode
        n = buf.pop_uint32()
        leaderboard_groups = []
        for i in range(n):
            angle = buf.pop_float32()
            leaderboard_groups.append(angle)
        self.subscriber.on_leaderboard_groups(angles=leaderboard_groups)
        self.player.world.leaderboard_groups = leaderboard_groups

    def parse_own_id(self, buf):  # new cell ID, respawned or split
        cid = buf.pop_uint32()
        player = self.player
        if not player.is_alive:  # respawned
            player.own_ids.clear()
            self.subscriber.on_respawn()
        # server sends empty name, assumes we set it here
        self.player.world.cells[cid].name = player.nick
        player.own_ids.add(cid)
        player.cells_changed()
        self.subscriber.on_own_id(cid=cid)

    def parse_world_rect(self, buf):  # world size
        left = buf.pop_float64()
        top = buf.pop_float64()
        right = buf.pop_float64()
        bottom = buf.pop_float64()
        self.subscriber.on_world_rect(left=left, top=top, right=right, bottom=bottom)
        self.player.world.top_left = Vec(top, left)
        self.player.world.bottom_right = Vec(bottom, right)
        self.player.center = self.world.center

    def parse_spectate_update(self, buf):
        # only in spectate mode
        x = buf.pop_float32()
        y = buf.pop_float32()
        scale = buf.pop_float32()
        self.player.center.set(x, y)
        self.player.scale = scale
        self.subscriber.on_spectate_update(pos=self.player.center, scale=scale)

    def parse_clear_cells(self, buf):
        # TODO clear cells packet is untested
        self.subscriber.on_clear_cells()
        self.player.world.cells.clear()
        self.player.own_ids.clear()
        self.player.cells_changed()

    def parse_debug_line(self, buf):
        # TODO debug line packet is untested
        x = buf.pop_float64()
        y = buf.pop_float64()
        self.subscriber.on_debug_line(x=x, y=y)

    def send_struct(self, fmt, *data):
        if self.is_connected:
            self.ws.send(struct.pack(fmt, *data))

    def send_handshake(self):
        self.send_struct('<BI', 254, 5)
        self.send_struct('<BI', 255, handshake_version)

    def send_token(self, token):
        self.send_struct('<B%iB' % len(token), 80, *map(ord, token))

    def send_respawn(self):
        nick = self.player.nick
        self.send_struct('<B%iH' % len(nick), 0, *map(ord, nick))

    def send_target(self, x, y, cid=0):
        self.send_struct('<BhhI', 16, int(x), int(y), cid)

    def send_spectate(self):
        self.send_struct('<B', 1)

    def send_split(self):
        self.send_struct('<B', 17)

    def send_shoot(self):
        self.send_struct('<B', 21)

    def send_explode(self):
        self.send_struct('<B', 20)
        self.player.own_ids.clear()
        self.player.cells_changed()
        self.ingame = False
        self.subscriber.on_death()
