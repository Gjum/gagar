from .drawutils import *
from .subscriber import Subscriber


class SolidBackground(Subscriber):
    def __init__(self, color=DARK_GRAY):
        self.color = color

    def on_draw_background(self, c, w):
        c.set_source_rgba(*self.color)
        c.paint()


class GridDrawer(Subscriber):
    def __init__(self, color=to_rgba(LIGHT_GRAY, .3)):
        self.color = color

    def on_draw_background(self, c, w):
        wl, wt = w.world_to_screen_pos(w.world.top_left)
        wr, wb = w.world_to_screen_pos(w.world.bottom_right)

        # grid
        c.set_source_rgba(*self.color)
        c.set_line_width(.5)

        for y in frange(wt, wb, 50 * w.screen_scale):
            c.move_to(wl, y)
            c.line_to(wr, y)
            c.stroke()

        for x in frange(wl, wr, 50 * w.screen_scale):
            c.move_to(x, wt)
            c.line_to(x, wb)
            c.stroke()


class WorldBorderDrawer(Subscriber):
    def on_draw_background(self, c, w):
        wl, wt = w.world_to_screen_pos(w.world.top_left)
        wr, wb = w.world_to_screen_pos(w.world.bottom_right)
        c.set_line_width(4)
        c.set_source_rgba(*to_rgba(LIGHT_GRAY, .5))
        c.rectangle(wl, wt, wr-wl, wb-wt)
        c.stroke()
