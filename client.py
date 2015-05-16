import struct
import websocket

def nice_hex(buffer):
    specials = {
        '\r': '\\r',
        '\n': '\\n',
        ' ': '␣',
        }
    nice_bytes = []
    hex_seen = False
    for b in buffer:
        if 33 <= int(b) <= 126:  # printable
            if hex_seen:
                nice_bytes.append(' ')
                hex_seen = False
            nice_bytes.append('%c' % b)
        elif chr(b) in specials:
            if hex_seen:
                nice_bytes.append(' ')
                hex_seen = False
            nice_bytes.append(specials[chr(b)])
        else:
            if not hex_seen:
                nice_bytes.append(' 0x')
                hex_seen = True
            nice_bytes.append('%02x' % b)
    return ''.join(nice_bytes)

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
        while 0 != self.peek_uint16():
            c = self.pop_uint16()
            l_name.append(chr(c))
        return ''.join(l_name)

    def peek_values(self, fmt):
        return struct.unpack_from(fmt, self.buffer, 0)

    def peek_uint8(self):
        return self.peek_values('<B')[0]

    def peek_uint16(self):
        return self.peek_values('<H')[0]

    def peek_uint32(self):
        return self.peek_values('<I')[0]

class PlayerCell:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 0
        self.name = ''
        self.virus = False

####################

msg_handshake = lambda: struct.pack('<BI', 255, 1)
msg_nick = lambda nick: struct.pack('<B%iH' % len(nick), 0, *map(ord, nick))
msg_update = lambda x, y: struct.pack('<BddI', 16, x, y, 0)
msg_spectate = lambda: struct.pack('<B', 1)

## special msgs
# spectate: send uint8 1
# space/tap: send update; send uint8 17
# q: send uint8 18; send uint8 19
# w: send update; send uint8 21
##

####################

cell = PlayerCell()

def parse_message(buf):
    s = BufferStruct(buf)
    ident = s.pop_uint8()
    if 16 == ident:  # world update?
        # sent very often, probably every "tick"

        # something is eaten?
        n = s.pop_uint16()
        print('eaten:', n)
        for d in range(n):
            ca = s.pop_uint32()
            cb = s.pop_uint32()
            # print('  ', ca, 'destroys', cb)
            if ca and cb:
                pass  # b.destroy(); b.xy = a.xy
        # create/update cells
        while 0 != s.peek_uint32():
            cid = s.pop_uint32()
            cx = s.pop_float32()
            cy = s.pop_float32()
            csize = s.pop_float32()
            color = s.pop_uint32()  # just skip TODO parse color
            bitmask = s.pop_uint8()
            is_virus = bool(bitmask & 1)
            is_agitated = bool(bitmask & 16)
            skips = 0  # lolwtf
            if bitmask & 2: skips += 4
            if bitmask & 4: skips += 8
            if bitmask & 8: skips += 16
            for i in range(skips): s.pop_uint8()
            cname = s.pop_str()
            print('  Virus' if is_virus else '  Cell ',
                  cid, cname, 'at %.2f %.2f' % (cx, cy),
                  'size: %.2f' % csize, 'color: #%06x' % color,
                  'agitated' if is_agitated else '')

        # keep only the following cells
        s.pop_uint16()  # 2 byte just skipped? lol
        keep = []
        n = s.pop_uint32()
        for e in range(n):
            keep.append(s.pop_uint32())
        # sort out other cells

    elif 49 == ident:  # leaderboard of names
        # sent every 500ms
        # only in free for all mode
        n = s.pop_uint32()
        leaderboard_names = []
        for i in range(n):
            l_id = s.pop_uint32()
            l_name = s.pop_str()
            leaderboard_names.append((l_id, l_name))
        print('  Leaderboard:')
        for l_id, l_name in leaderboard_names:
            print('    ', '%11i' % l_id, l_name)

    elif 50 == ident:  # leaderboard of groups
        # sent every 500ms
        # only in group mode
        n = s.pop_uint32()
        leaderboard_angles = []
        for i in range(n):
            angle = s.pop_float32()
            leaderboard_angles.append(angle)
        import sys;sys.exit()

    elif 32 == ident:  # new own ID?
        # not sent in passive mode
        # first on respawn
        # B.push(d.getUint32(1, !0));
        val32 = s.pop_uint32()
        print('  New ID:', val32)
        import sys;sys.exit()

    elif 17 == ident:  # pos/size update? "moved wrongly"?
        # not sent in passive mode
        # not sent in active mode?
        cell.x = x = s.pop_float32()
        cell.y = y = s.pop_float32()
        cell.size = size = s.pop_float32()
        print('  Moved wrongly: xy:', x, y, 'size:', size)
        import sys;sys.exit()

    elif 20 == ident:  # reset cell?
        # not sent in passive mode
        # sent on death?
        # g = []; B = [];
        print('  [20]')

    elif 64 == ident:  # info about updated area?
        # sent on connection
        # sent on server change
        a = s.pop_float64()
        b = s.pop_float64()
        c = s.pop_float64()
        d = s.pop_float64()
        x = (c + a) / 2  # move shown area to center?
        y = (d + b) / 2
        print('  ab:', a, b, '\n  cd:', c, d, '\n  xy:', x, y)

    elif ord('H') == ident:  # "Hello Hello Hello"
        pass  # print('  Well hello, good sir.')

    else:
        print('  Unexpected ident 0x%02x' % ident)

def on_message(ws, buf):
    ident = buf[0]
    print('RECV', ident, nice_hex(buf))
    try:
        parse_message(buf)
    except BufferUnderflowError as e:
        print('ERROR parsing ident', ident, 'failed:', e.args[0],
              nice_hex(buf))
        import sys;sys.exit()

def on_error(ws, error):
    print('ERROR', error)

def on_close(ws):
    print('CLOSED')

def on_open(ws):
    ws.send(msg_handshake())
    # import random
    # nick = ''.join(['aeiouy'[random.randint(0, 5)]]*5)
    # print('Nick:', nick)
    # ws.send(msg_nick(nick))
    # ws.send(msg_spectate())

####################

def get_url():
    import urllib.request
    addr = urllib.request.urlopen('http://m.agar.io')\
            .read().decode().split('\n')[0]
    #addr = '213.219.37.141:443'
    url = 'ws://%s' % addr
    print('Got url', url)
    return url

if __name__ == "__main__":
    # websocket.enableTrace(True)
    ws = websocket.WebSocketApp(get_url(),
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(origin='http://agar.io')
