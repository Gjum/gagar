from collections import deque
from time import time
from agario.vec import Vec

from .drawutils import *
from .subscriber import Subscriber


class Minimap(Subscriber):
    def on_draw_hud(self, c, w):
        if w.world.size:
            minimap_w = w.win_size.x / 5
            minimap_size = Vec(minimap_w, minimap_w)
            minimap_scale = minimap_size.x / w.world.size.x
            minimap_offset = w.win_size - minimap_size

            def world_to_mm(world_pos):
                pos_from_top_left = world_pos - w.world.top_left
                return minimap_offset + pos_from_top_left * minimap_scale

            line_width = c.get_line_width()
            c.set_line_width(1)

            # minimap border
            c.set_source_rgba(*to_rgba(LIGHT_GRAY, .5))
            c.rectangle(*as_rect(minimap_offset, size=minimap_size))
            c.stroke()

            # the area visible in window
            c.rectangle(*as_rect(world_to_mm(w.screen_to_world_pos(Vec(0,0))),
                                 world_to_mm(w.screen_to_world_pos(w.win_size))))
            c.stroke()

            for cell in w.world.cells.values():
                draw_circle_outline(c, world_to_mm(cell.pos),
                                    cell.size * minimap_scale,
                                    color=to_rgba(cell.color, .8))

            c.set_line_width(line_width)


class Leaderboard(Subscriber):
    def on_draw_hud(self, c, w):
        width = 200
        lb_x = w.win_size.x - width-10

        c.set_source_rgba(*to_rgba(BLACK, .6))
        c.rectangle(lb_x, 10,
                    width, 50 + 24 * len(w.world.leaderboard_names))
        c.fill()

        player_cid = min(c.cid for c in w.player.own_cells) \
            if w.player and w.player.own_ids else -1

        draw_text_center(c, (lb_x+width//2, 35), "Leaderboard", color=WHITE, size=30)

        for rank, (cid, name) in enumerate(w.world.leaderboard_names):
            rank += 1  # start at rank 1
            name = name or 'An unnamed cell'
            text = '%i. %s' % (rank, name)
            if cid == player_cid:
                color = RED
            elif cid in w.world.cells:
                color = LIGHT_BLUE
            else:
                color = WHITE
            draw_text_left(c, (lb_x+10, 50+24*rank), text, color=color, size=20)


class MassGraph(Subscriber):
    def __init__(self, client):
        self.client = client
        self.graph = []

    def on_respawn(self):
        self.graph.clear()

    def on_world_update_post(self):
        player = self.client.player
        if not player.is_alive:
            return
        sample = (
            player.total_mass,
            sorted((c.cid, c.mass) for c in player.own_cells)
        )
        self.graph.append(sample)

    def on_draw_hud(self, c, w):
        if not self.graph:
            return
        scale_x = w.INFO_SIZE / len(self.graph)
        scale_y = w.INFO_SIZE / (max(self.graph)[0] or 10)
        c.set_source_rgba(*to_rgba(BLUE, .3))
        c.move_to(0, 0)
        for i, (total_mass, masses) in enumerate(reversed(self.graph)):
            c.line_to(i * scale_x, total_mass * scale_y)
        c.line_to(w.INFO_SIZE, 0)
        c.fill()


class FpsMeter(Subscriber):
    def __init__(self, queue_len):
        self.draw_last = self.world_last = time()
        self.draw_times = deque([0]*queue_len, queue_len)
        self.world_times = deque([0]*queue_len, queue_len)

    def on_world_update_post(self):
        now = time()
        dt = now - self.world_last
        self.world_last = now
        self.world_times.appendleft(dt)

    def on_draw_hud(self, c, w):
        c.set_line_width(2)
        c.set_source_rgba(*to_rgba(RED, .3))
        for i, t in enumerate(self.draw_times):
            c.move_to(*(w.win_size - Vec(4*i - 2, 0)))
            c.rel_line_to(0, -t * 1000)
            c.stroke()

        c.set_source_rgba(*to_rgba(YELLOW, .3))
        for i, t in enumerate(self.world_times):
            c.move_to(*(w.win_size - Vec(4*i, 0)))
            c.rel_line_to(0, -t * 1000)
            c.stroke()

        # 25, 30, 60 FPS marks
        c.set_line_width(.5)
        graph_width = 4 * len(self.draw_times)
        for fps, color in ((25,ORANGE), (30,GREEN), (60,BLUE)):
            c.set_source_rgba(*to_rgba(color, .3))
            c.move_to(*(w.win_size - Vec(graph_width, 1000/fps)))
            c.rel_line_to(graph_width, 0)
            c.stroke()

        now = time()
        dt = now - self.draw_last
        self.draw_last = now
        self.draw_times.appendleft(dt)
