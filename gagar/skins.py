import io
from threading import Thread
import urllib.request

import cairo

from agarnet.utils import default_headers, special_names
from .drawutils import TWOPI
from .subscriber import Subscriber


skin_cache = {}  # raw PNG data
skin_surface_cache = {}  # images in cairo format


def get_skin(name):
    name = name.lower()
    if name not in skin_cache:
        # load in separate thread, return None for now
        skin_cache[name] = None

        def loader():
            skin_url = 'http://agar.io/skins/%s.png' % urllib.request.quote(
                name)
            opener = urllib.request.build_opener()
            opener.addheaders = default_headers
            skin_cache[name] = opener.open(skin_url).read()

        t = Thread(target=loader)
        t.setDaemon(True)
        t.start()
    return skin_cache[name]


class CellSkins(Subscriber):
    def on_draw_cells(self, c, w):
        c = c._cairo_context
        for cell in w.world.cells.values():
            name = cell.name.lower()
            if name in special_names:
                skin_data = get_skin(name)
                if not skin_data:  # image is still being loaded
                    continue  # TODO fancy loading circle animation
                if name not in skin_surface_cache:
                    skin_surface_cache[name] = cairo.ImageSurface.create_from_png(io.BytesIO(skin_data))
                skin_surface = skin_surface_cache[name]
                skin_radius = skin_surface.get_width() / 2
                c.save()
                c.translate(*w.world_to_screen_pos(cell.pos))
                scale = w.world_to_screen_size(cell.size / skin_radius)
                c.scale(scale, scale)
                c.translate(-skin_radius, -skin_radius)
                c.set_source_surface(skin_surface, 0, 0)
                c.new_sub_path()
                c.arc(skin_radius, skin_radius, skin_radius, 0, TWOPI)
                c.fill()
                c.restore()
