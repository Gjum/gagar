"""
http://doswa.com/2009/07/13/circle-segment-intersectioncollision.html
Slightly modified for pyagario by Gjum code.gjum@gmail.com
"""

import math

class Vec(object):
    __slots__ = ('x', 'y')

    def __init__(self, x=(0, 0), y=None):
        if y is not None:
            self.x = x
            self.y = y
        else:
            try:
                self.x = x.x
                self.y = x.y
            except AttributeError:
                try:
                    self.x, self.y = x
                except TypeError:
                    raise TypeError("Invalid parameters")

    def copy(self):
        return Vec(self.x, self.y)

    def set(self, x, y):
        self.x = x
        self.y = y
        return self

    def iadd(self, v):
        self.x += v.x
        self.y += v.y
        return self

    def __add__(self, v):
        return self.copy().iadd(v)

    __radd__ = __add__
    __iadd__ = iadd

    def isub(self, v):
        self.x -= v.x
        self.y -= v.y
        return self

    __isub__ = isub

    def __sub__(self, v):
        return self.copy().isub(v)

    __rsub__ = __sub__

    def imul(self, s):
        self.x *= s
        self.y *= s
        return self

    def __mul__(self, s):
        if not isinstance(self, Vec):
            self, s = s, self
        return self.copy().imul(s)

    __rmul__ = __mul__

    def __imul__(self, s):
        if not isinstance(self, Vec):
            self, s = s, self
        return self.imul(s)

    def idiv(self, s):
        self.x /= s
        self.y /= s
        return self

    __idiv__ = idiv

    def __div__(self, s):
        return self.copy().idiv(s)

    __rdiv__ = __div__
    __truediv__ = __div__
    __rtruediv__ = __div__

    def ivdiv(self, v):
        self.x /= v.x
        self.y /= v.y
        return self

    def vdiv(self, v):
        return self.copy().ivdiv(v)

    def dot(self, v):
        return self.x * v.x + self.y * v.y

    def cross(self, v):
        return self.x * v.y - v.x * self.y

    def lensq(self):
        return self.dot(self)

    def len(self):
        return math.sqrt(self.lensq())

    def set_len(self, new_len):
        self.imul(new_len / self.len())

    def unit(self):
        lensq = self.lensq()
        if lensq == 1:
            return self
        return self.copy().idiv(math.sqrt(lensq))

    def iunit(self):
        lensq = self.lensq()
        if lensq == 1:
            return self
        return self.idiv(math.sqrt(lensq))

    def iperp(self):
        self.x, self.y = -self.y, self.x
        return self

    def perp(self):
        return self.copy().iperp()

    def proj(self, v):
        return self.dot(v.unit())

    def proj_vec(self, v):
        u = v.unit()
        return u.imul(self.dot(u))

    def ineg(self):
        self.x = -self.x
        self.y = -self.y
        return self

    def neg(self):
        return self.copy().ineg()

    __neg__ = neg

    def irot(self, angle_degrees):
        rad = math.radians(angle_degrees)
        c = math.cos(rad)
        s = math.sin(rad)
        self.x = self.x * c - self.y * s
        self.y = self.x * s + self.y * c
        return self

    def rot(self, angle_degrees):
        return self.copy().irot(angle_degrees)

    def angle(self):
        if self.lensq == 0:
            return 0
        return math.degrees(math.atan2(self.y, self.x))

    def set_angle(self, angle_degrees):
        self.x = self.len()
        self.y = 0
        self.rot(angle_degrees)

    def angle_to(self, other):
        cross = self.x * other[1] - self.y * other[0]
        dot = self.x * other[0] + self.y * other[1]
        return math.degrees(math.atan2(cross, dot))

    def __nonzero__(self):
        return bool(self.x or self.y)

    def __len__(self):
        return 2

    def __getitem__(self, key):
        if key == 0 or key == "x":
            return self.x
        if key == 1 or key == "y":
            return self.y
        raise IndexError

    def __setitem__(self, key, value):
        if key == 0 or key == "x":
            self.x = value
        if key == 1 or key == "y":
            self.y = value
        raise IndexError

    def __iter__(self):
        yield self.x
        yield self.y

    def __str__(self):
        return "Vec(%.3f, %.3f)" % tuple(self)
