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

def to_rgba(c, a):
    return c[0], c[1], c[2], a

def draw_text_center(c, center, text, *args, **kwargs):
    try:
        x_bearing, y_bearing, text_width, text_height, x_advance, y_advance \
            = c.text_extents(text)
        cx, cy = center
        x = cx - x_bearing - text_width / 2
        y = cy - y_bearing - text_height / 2
        draw_text_left(c, (x, y), text, *args, **kwargs)
    except UnicodeEncodeError:
        pass

def draw_text_left(c, pos, text,
                   color=WHITE, shadow=None, size=12, face='sans'):
    try:
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
