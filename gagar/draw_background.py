from .drawutils import *
from .subscriber import Subscriber


class SolidBackground(Subscriber):
    def __init__(self, color=DARK_GRAY):
        self.color = color

    def on_draw_background(self, c, w):
        c.fill_color(self.color)


class GridDrawer(Subscriber):
    def on_draw_background(self, c, w):
        wl, wt = w.world_to_screen_pos(w.world.top_left)
        wr, wb = w.world_to_screen_pos(w.world.bottom_right)
        grid_spacing = w.world_to_screen_size(50)
        for y in frange(wt, wb, grid_spacing):
            c.draw_line((wl, y), (wr, y), width=.5,
                        color=to_rgba(LIGHT_GRAY, .3))
        for x in frange(wl, wr, grid_spacing):
            c.draw_line((x, wt), (x, wb), width=.5,
                        color=to_rgba(LIGHT_GRAY, .3))


class WorldBorderDrawer(Subscriber):
    def on_draw_background(self, c, w):
        wl, wt = w.world_to_screen_pos(w.world.top_left)
        wr, wb = w.world_to_screen_pos(w.world.bottom_right)
        c.stroke_rect((wl, wt), (wr, wb), width=4,
                      color=to_rgba(LIGHT_GRAY, .5))
