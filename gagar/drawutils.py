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


class Canvas(object):
    """Bundles all drawing methods, providing a useful abstraction layer."""

    def __init__(self, cairo_context):
        self._cairo_context = cairo_context

    def draw_text(self, pos, text, size=12, face='sans',
                  align=None, anchor_x='left', anchor_y='baseline',
                  color=WHITE, shadow=None, outline=None):
        c = self._cairo_context
        try:
            c.select_font_face(face)
            c.set_font_size(size)

            # align overrides anchors
            if align:
                anchor_x = align
                anchor_y = 'baseline'

            # move text to the correct position
            x_bearing, y_bearing, text_width, text_height, x_advance, y_advance \
                = c.text_extents(text)
            x, y = map(int, pos)
            x -= x_bearing

            if anchor_x == 'center':
                x -= text_width // 2
            elif anchor_x == 'right':
                x -= text_width
            elif anchor_x == 'left':
                pass
            else:
                raise ValueError('Invalid anchor_x "%s"' % anchor_x)

            if anchor_y == 'center':
                y -= y_bearing + text_height // 2
            elif anchor_y == 'top':
                y -= y_bearing
            elif anchor_y == 'bottom':
                y -= y_bearing + text_height
            elif anchor_y == 'baseline':
                pass
            else:
                raise ValueError('Invalid anchor_y "%s"' % anchor_y)

            # optionally, draw shadow/outline behind the text
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

            # draw the text itself
            c.move_to(x, y)
            c.set_source_rgba(*color)
            c.text_path(text)
            c.fill()
        except UnicodeEncodeError:  # tried to display invalid chars
            pass

    def fill_circle(self, pos, radius, color=None):
        c = self._cairo_context
        x, y = pos
        if color: c.set_source_rgba(*color)
        c.new_sub_path()
        c.arc(x, y, radius, 0, TWOPI)
        c.fill()

    def stroke_circle(self, pos, radius, width=None, color=None):
        c = self._cairo_context
        x, y = pos
        if width: c.set_line_width(width)
        if color: c.set_source_rgba(*color)
        c.new_sub_path()
        c.arc(x, y, radius, 0, TWOPI)
        c.stroke()

    def fill_rect(self, left_top, right_bottom=None, size=None, color=None):
        c = self._cairo_context
        left, top = left_top
        if color: c.set_source_rgba(*color)
        if right_bottom:
            right, bottom = right_bottom
            c.rectangle(left, top, right - left, bottom - top)
        elif size:
            c.rectangle(left, top, *size)
        c.fill()

    def stroke_rect(self, left_top, right_bottom=None, size=None,
                          width=None, color=None):
        c = self._cairo_context
        left, top = left_top
        if width: c.set_line_width(width)
        if color: c.set_source_rgba(*color)
        if right_bottom:
            right, bottom = right_bottom
            c.rectangle(left, top, right - left, bottom - top)
        elif size:
            c.rectangle(left, top, *size)
        c.stroke()

    def draw_line(self, start, *points, relative=None, width=None, color=None):
        c = self._cairo_context
        if width: c.set_line_width(width)
        if color: c.set_source_rgba(*color)
        c.move_to(*start)
        if relative:
            c.rel_line_to(*relative)
        else:
            for point in points:
                c.line_to(*point)
        c.stroke()

    def fill_polygon(self, start, *points, color=None):
        c = self._cairo_context
        if color: c.set_source_rgba(*color)
        c.move_to(*start)
        for point in points:
            c.line_to(*point)
        c.fill()

    def fill_color(self, color):
        c = self._cairo_context
        c.set_source_rgba(*color)
        c.paint()
