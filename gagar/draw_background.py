from .drawutils import *
from .subscriber import Subscriber


class SolidBackground(Subscriber):
    def __init__(self, color=DARK_GRAY):
        self.color = color

    def on_draw_background(self, c, w):
        c = c._cairo_context
        c.set_source_rgba(*self.color)
        c.paint()


class GridDrawer(Subscriber):
    def on_draw_background(self, c, w):
        c = c._cairo_context
        wl, wt = w.world_to_screen_pos(w.world.top_left)
        wr, wb = w.world_to_screen_pos(w.world.bottom_right)
        grid_spacing = w.world_to_screen_size(50)
        c.set_source_rgba(*to_rgba(LIGHT_GRAY, .3))
        c.set_line_width(.5)
        for y in frange(wt, wb, grid_spacing):
            c.move_to(wl, y)
            c.line_to(wr, y)
            c.stroke()
        for x in frange(wl, wr, grid_spacing):
            c.move_to(x, wt)
            c.line_to(x, wb)
            c.stroke()


class WorldBorderDrawer(Subscriber):
    def on_draw_background(self, c, w):
        c = c._cairo_context
        wl, wt = w.world_to_screen_pos(w.world.top_left)
        wr, wb = w.world_to_screen_pos(w.world.bottom_right)
        c.set_line_width(4)
        c.set_source_rgba(*to_rgba(LIGHT_GRAY, .5))
        c.rectangle(wl, wt, wr-wl, wb-wt)
        c.stroke()
