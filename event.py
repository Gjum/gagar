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

class Channel(object):
    """Manages multiple subscribers and broadcasts messages to them."""

    def __init__(self):
        self.subscribers = []

    def subscribe(self, subscriber):
        self.subscribers.append(subscriber)

    def unsubscribe(self, subscriber):
        self.subscribers.remove(subscriber)

    def broadcast(self, event, **data):
        for subscriber in self.subscribers[:]:
            try:
                subscriber.on_event(event, **data)
            except Exception as e:
                print('Handler %s failed on %s %s'
                      % (subscriber.__class__.__name__, event, data))
                raise e


class Subscriber(object):
    """Base class. `on_event(event, **data)` calls `self.on_<event>(**data)`."""

    def __init__(self, channel):
        self.channel = channel
        channel.subscribe(self)

    def set_channel(self, channel):
        channel.unsubscribe(self)
        self.channel = channel
        channel.subscribe(self)

    def on_event(self, event, **data):
        func = getattr(self, 'on_%s' % event, None)
        if func: func(**data)


class Collector(object):
    """ Collects events from multiple channels and broadcasts them into one. """

    def __init__(self, output, *inputs):
        self.output = output
        self.inputs = inputs
        for channel in self.inputs:
            channel.subscribe(self)

    def set_inputs(self, inputs):
        for channel in self.inputs:
            channel.unsubscribe(self)
        self.inputs = inputs
        for channel in self.inputs:
            channel.subscribe(self)

    def on_event(self, event, **data):
        self.output.broadcast(event, **data)


class Distributor(object):
    """ Passes any event to multiple channels. """

    def __init__(self, *channels):
        self.channels = channels

    def on_event(self, event, **data):
        for channel in self.channels:
            channel.broadcast(event, **data)
