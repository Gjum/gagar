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

class BufferUnderflowError(struct.error):
    def __init__(self, fmt, buf):
        self.fmt = fmt
        self.buf = buf
        self.args = ('Buffer too short: wanted %i %s, got %i %s'
                     % (struct.calcsize(fmt), fmt, len(buf), buf),)

class BufferStruct(object):
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

    def pop_int8(self):
        return self.pop_values('<b')[0]

    def pop_uint8(self):
        return self.pop_values('<B')[0]

    def pop_int16(self):
        return self.pop_values('<h')[0]

    def pop_uint16(self):
        return self.pop_values('<H')[0]

    def pop_int32(self):
        return self.pop_values('<i')[0]

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
