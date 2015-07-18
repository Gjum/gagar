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


class Subscriber(object):
    """Base class for event handlers via on_*() methods."""

    def __getattr__(self, func_name):
        # still throw error when not getting an on_*() method/attribute
        if 'on_' != func_name[:3]:
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, func_name))
        return lambda *args, **kwargs: None


class MultiSubscriber(Subscriber):
    """Distributes method calls to multiple subscribers."""

    def __init__(self, *subs):
        self.subs = list(subs)

    def sub(self, subscriber):
        self.subs.append(subscriber)
        return subscriber

    def __getattr__(self, func_name):
        # still throw error when not getting an on_*() method/attribute
        super(self.__class__, self).__getattr__(func_name)

        def wrapper(*args, **kwargs):
            for sub in self.subs:
                handler = getattr(sub, func_name, None)
                if handler:
                    handler(*args, **kwargs)

        return wrapper
