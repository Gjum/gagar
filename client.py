from collections import defaultdict
import struct
from sys import stderr
import select
import websocket

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
        return nice_hex(self.buffer)

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

class AgarClient:
    def __init__(self):
        self.ws = None
        self.handlers = defaultdict(list)
        self.crash_on_errors = False
        self.connected = False
        self.last_err = None  # TODO check if crashing iff True

    def add_handler(self, ident, handler):
        self.handlers[ident].append(handler)

    def handle(self, ident, **data):
        if not self.connected:
            return
        for handler in self.handlers[ident]:
            # noinspection PyBroadException
            try:
                handler(**data)
            except Exception:
                if self.crash_on_errors:
                    print('Handler failed on ident', ident, data, file=stderr)
                    raise

    def connect(self, url):
        self.open_socket(url)
        self.run_forever()
        self.on_close()

    def open_socket(self, url):
        self.ws = websocket.WebSocket()
        self.ws.connect(url, origin='http://agar.io')
        self.connected = True
        self.handle('open')
        return self.ws

    def run_forever(self):
        while 1:
            r, w, e = select.select((self.ws.sock, ), (), ())
            if r:
                self.on_message(self.ws.recv())
            elif e:
                self.handle('error', error=e)

    def on_close(self):
        self.handle('close')
        self.connected = False
        self.ws = None
        if self.last_err:
            raise self.last_err

    def disconnect(self):
        self.ws.keep_running = False
        self.connected = False

    def on_message(self, msg):
        ident = msg[0]
        self.handle('raw_%02i' % ident, raw=msg)
        try:
            self.parse_message(msg)
        except BufferUnderflowError as e:
            print('ERROR parsing ident', ident, 'failed:',
                  e.args[0], nice_hex(msg), file=stderr)
        except Exception as e:
            if self.crash_on_errors:
                self.last_err = e
                self.disconnect()
                raise

    def parse_message(self, msg):
        s = BufferStruct(msg)
        ident = s.pop_uint8()

        if 16 == ident:  # world update?
            # sent very often, probably every "tick"

            # something is eaten?
            n = s.pop_uint16()
            for i in range(n):
                ca = s.pop_uint32()
                cb = s.pop_uint32()
                self.handle('cell_eaten', a=ca, b=cb)

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

            # keep only the following cells
            s.pop_uint16()  # 2 byte just skipped? lol
            keep_cells = []
            n = s.pop_uint32()
            for e in range(n):
                keep_cells.append(s.pop_uint32())
            # sort out other cells
            self.handle('cell_keep', keep_cells=keep_cells)

        elif 49 == ident:  # leaderboard of names
            # sent every 500ms
            # only in free for all mode
            n = s.pop_uint32()
            leaderboard = []
            for i in range(n):
                l_id = s.pop_uint32()
                l_name = s.pop_str()
                leaderboard.append((l_id, l_name))
            self.handle('leaderboard_names', leaderboard=leaderboard)

        elif 50 == ident:  # leaderboard of groups
            # sent every 500ms
            # only in group mode
            n = s.pop_uint32()
            angles = []
            for i in range(n):
                angle = s.pop_float32()
                angles.append(angle)
            self.handle('leaderboard_angles', angles=angles)

        elif 32 == ident:  # new own ID?
            # not sent in passive mode
            # first on respawn
            # B.push(d.getUint32(1, !0));
            cid = s.pop_uint32()
            self.handle('new_id', cid=cid)

        elif 17 == ident:  # pos/size update? "moved wrongly"?
            # not sent in passive mode
            # not sent in active mode?
            cx = s.pop_float32()
            cy = s.pop_float32()
            size = s.pop_float32()
            self.handle('moved_wrongly', x=cx, y=cy, size=size)

        elif 20 == ident:  # reset cell?
            # not sent in passive mode
            # sent on death?
            # g = []; B = [];
            self.handle('20')

        elif 64 == ident:  # info about updated area?
            # sent on connection
            # sent on server change
            left = s.pop_float64()
            top = s.pop_float64()
            right = s.pop_float64()
            bottom = s.pop_float64()
            self.handle('area', left=left, top=top, right=right, bottom=bottom)

        elif ord('H') == ident:  # "HelloHelloHello"
            # sent after initial connection setup
            self.handle('hello')

        else:
            print('  Unexpected ident 0x%02x' % ident, file=stderr)

    def send_struct(self, fmt, *data):
        if not self.ws:
            raise ValueError('Not connected to server')
        self.ws.send(struct.pack(fmt, *data))

    def send_handshake(self):
        self.send_struct('<BI', 255, 1)

    def send_nick(self, nick):
        self.send_struct('<B%iH' % len(nick), 0, *map(ord, nick))

    def send_mouse(self, x, y):
        self.send_struct('<BddI', 16, x, y, 0)

    def send_spectate(self):
        self.send_struct('<B', 1)

    def send_split(self):
        self.send_struct('<B', 17)

    def send_shoot(self):
        self.send_struct('<B', 21)

####################

specials = {
    '\r': '\\r',
    '\n': '\\n',
    ' ': '␣',
}

def nice_hex(buffer):
    nice_bytes = []
    hex_seen = False
    for b in buffer:
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

def nice_hex_block(buffer, width=32):
    lines = []
    for lineno in range(len(buffer) // width + 1):  # should stop at break below
        nice_bytes = []
        for b in buffer[:width]:
            if chr(b) in specials:
                nice_bytes.append('%2s' % specials[chr(b)])
            elif 33 <= int(b) <= 126:  # printable
                nice_bytes.append(' %c' % b)
            elif b == 0:
                nice_bytes.append(' .')
            else:
                nice_bytes.append(' ~')

        line = '%04i %-*s\n     %-*s' % (
            lineno * width,
            3 * width,
            ' '.join('%02x' % b for b in buffer[:width]),
            3 * width,
            ' '.join(nice_bytes),
        )
        lines.append(line)
        buffer = buffer[width:]
        if len(buffer) <= 0:
            break
    return '\n'.join(lines)

def find_strings(buffer):
    # TODO split at 0x0000, go backwards from there, keep Little Endianness in mind
    string = []
    find0 = True
    for i, b in enumerate(buffer):
        if find0 and b == 0:
            find0 = False
        elif not find0 and 32 <= int(b) <= 126:
            string.append(chr(b))
            find0 = True
        else:
            string = ''.join(string)
            if len(string) > 2:
                yield string
            string = []
            find0 = True

####################

def print_cell_info(cid, x, y, size, name, color, is_virus, is_agitated):
    print('Virus' if is_virus else 'Cell ',
          '%8i' % cid, 'at %.2f %.2f' % (x, y),
          'size: %.2f' % size, 'color: #%02x%02x%02x' % color,
          '"%s"' % name, 'agitated' if is_agitated else '')

def print_leaderboard_names(leaderboard):
    print('Leaderboard:')
    for l_id, l_name in leaderboard:
        print('  %11i' % l_id, l_name)

def print_leaderboard_angles(angles):
    print('Leaderboard: angles', angles)

####################

def get_url(region='EU-London'):
    import urllib.request
    addr = urllib.request.urlopen('http://m.agar.io', data=region.encode())\
            .read().decode().split('\n')[0]
    return 'ws://%s' % addr

def main():
    client = AgarClient()
    client.crash_on_errors = True
    client.add_handler('hello', lambda **data: client.send_handshake())
    client.add_handler('cell_info', print_cell_info)
    client.add_handler('leaderboard_names', print_leaderboard_names)
    client.add_handler('leaderboard_angles', print_leaderboard_angles)

    # websocket.enableTrace(True)
    url = get_url()
    print('Got url', url)
    try:
        client.connect(url)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    print('Done')

if __name__ == "__main__":
    main()