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

TWOPI = 6.28318530717958

BLACK = (0,0,0)
WHITE = (1,1,1)
GRAY = (.5,)*3
DARK_GRAY = (.2,)*3
LIGHT_GRAY = (.7,)*3

RED = (1,0,0)
GREEN = (0,1,0)
BLUE = (0,0,1)
YELLOW = (1,1,0)
TURQUOISE = (0,1,1)
FUCHSIA = (1,0,1)

ORANGE = (1,.5,0)
PURPLE = (.5,0,1)
LIGHT_GREEN = (.5,1,.5)
LIGHT_BLUE = (.5,.5,1)

def frange(start, end, step):
    """same as range(), but allows using floats"""
    while start < end:
        yield start
        start += step

def to_rgba(c, a):
    return c[0], c[1], c[2], a

def as_rect(tl, br=None, size=None):
    """Make tuple from 2 Vecs. Either bottom-right or rect size must be given."""
    if size:
        return tl.x, tl.y, size.x, size.y
    else:
        return tl.x, tl.y, br.x-tl.x, br.y-tl.y

def draw_text(c, pos, text, align='left', color=WHITE, shadow=None, outline=None, size=12, face='sans'):
    try:
        c.select_font_face(face)
        c.set_font_size(size)

        align = align.lower()
        if align == 'center':
            x_bearing, y_bearing, text_width, text_height, x_advance, y_advance \
                = c.text_extents(text)
            x = int(pos[0] - x_bearing - text_width / 2)
            y = int(pos[1] - y_bearing - text_height / 2)
        elif align == 'left':
            x, y = map(int, pos)
        elif align == 'right':
            x_bearing, y_bearing, text_width, text_height, x_advance, y_advance \
                = c.text_extents(text)
            x = int(pos[0] - x_bearing - text_width)
            y = int(pos[1])
        else:
            raise ValueError('Invalid alignment "%s"' % align)

        if shadow:
            s_color, s_offset = shadow
            s_dx, s_dy = s_offset
            c.move_to(x + s_dx, y + s_dy)
            c.set_source_rgba(*s_color)
            c.show_text(text)

        if outline:
            o_color, o_size = outline
            c.move_to(x, y)
            c.set_line_width(o_size)
            c.set_source_rgba(*o_color)
            c.text_path(text)
            c.stroke()

        c.move_to(x, y)
        c.set_source_rgba(*color)
        c.text_path(text)
        c.fill()
    except UnicodeEncodeError:
        pass

def draw_circle(c, pos, radius, color=None):
    x, y = pos
    if color:
        c.set_source_rgba(*color)
    c.new_sub_path()
    c.arc(x, y, radius, 0, TWOPI)
    c.fill()

def draw_circle_outline(c, pos, radius, color=None):
    x, y = pos
    if color:
        c.set_source_rgba(*color)
    c.new_sub_path()
    c.arc(x, y, radius, 0, TWOPI)
    c.stroke()
