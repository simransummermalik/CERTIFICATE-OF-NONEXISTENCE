"""Exact rigid motions for an architecture built on a quarter-inch grid.

Every length in this project is an integer number of quarter inches, and every
rotation is a whole number of quarter turns about the vertical axis. Nothing is
ever rounded, so a loop that fails to close fails by an exact amount.
"""

from __future__ import annotations

from dataclasses import dataclass

Q = 1                 # one quarter inch
INCH = 4 * Q
FOOT = 12 * INCH


def ft(feet: int = 0, inches: int = 0, quarters: int = 0) -> int:
    return feet * FOOT + inches * INCH + quarters * Q


def fmt_len(u: int, zero: str = "0′-0″") -> str:
    """Quarter-inch units -> architectural notation, e.g. 38′-6¼″."""
    if u == 0:
        return zero
    sign = "−" if u < 0 else ""
    u = abs(u)
    feet, rem = divmod(u, FOOT)
    inches, quarters = divmod(rem, INCH)
    frac = {0: "", 1: "¼", 2: "½", 3: "¾"}[quarters]
    return f"{sign}{feet}′-{inches}{frac}″"


def fmt_inches(u: int) -> str:
    """Quarter-inch units -> inches only, e.g. 7¼″."""
    sign = "−" if u < 0 else ""
    u = abs(u)
    inches, quarters = divmod(u, INCH)
    frac = {0: "", 1: "¼", 2: "½", 3: "¾"}[quarters]
    if inches == 0 and frac:
        return f"{sign}{frac}″"
    return f"{sign}{inches}{frac}″"


# Quarter-turn rotation matrices, counter-clockwise seen from above.
_ROT = {
    0: ((1, 0), (0, 1)),
    1: ((0, -1), (1, 0)),
    2: ((-1, 0), (0, -1)),
    3: ((0, 1), (-1, 0)),
}


def rot2(r: int, x: int, y: int) -> tuple[int, int]:
    (a, b), (c, d) = _ROT[r % 4]
    return a * x + b * y, c * x + d * y


@dataclass(frozen=True)
class Motion:
    """p  ->  R(r) p + t, with R a rotation about z by r quarter turns."""

    r: int = 0
    t: tuple[int, int, int] = (0, 0, 0)

    def __post_init__(self):
        object.__setattr__(self, "r", self.r % 4)

    def __matmul__(self, other: "Motion") -> "Motion":
        x, y = rot2(self.r, other.t[0], other.t[1])
        return Motion(self.r + other.r,
                      (x + self.t[0], y + self.t[1], other.t[2] + self.t[2]))

    def inv(self) -> "Motion":
        x, y = rot2(-self.r, -self.t[0], -self.t[1])
        return Motion(-self.r, (x, y, -self.t[2]))

    def apply(self, p: tuple[int, int, int]) -> tuple[int, int, int]:
        x, y = rot2(self.r, p[0], p[1])
        return x + self.t[0], y + self.t[1], p[2] + self.t[2]

    @property
    def is_identity(self) -> bool:
        return self.r == 0 and self.t == (0, 0, 0)

    def matrix(self) -> list[list[int]]:
        """Homogeneous 4x4 integer matrix."""
        (a, b), (c, d) = _ROT[self.r]
        x, y, z = self.t
        return [[a, b, 0, x], [c, d, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]

    def fixed_point(self):
        """For a pure rotation (r != 0): the point in the plan it turns about."""
        if self.r == 0:
            return None
        # Solve (I - R) p = t in exact rationals.
        from fractions import Fraction as F
        (a, b), (c, d) = _ROT[self.r]
        m = ((1 - a, -b), (-c, 1 - d))
        det = m[0][0] * m[1][1] - m[0][1] * m[1][0]
        tx, ty = self.t[0], self.t[1]
        px = F(m[1][1] * tx - m[0][1] * ty, det)
        py = F(-m[1][0] * tx + m[0][0] * ty, det)
        return px, py

    def describe(self) -> str:
        if self.is_identity:
            return "identity"
        parts = []
        if self.r:
            parts.append(f"rotation {90 * self.r}°")
        x, y, z = self.t
        if self.r == 0 and (x or y):
            parts.append(f"shift ({fmt_len(x)}, {fmt_len(y)})")
        if z:
            parts.append(f"rise {fmt_len(z)}")
        return " · ".join(parts)


IDENTITY = Motion()
HALF_TURN = Motion(2)


def translate(x: int = 0, y: int = 0, z: int = 0) -> Motion:
    return Motion(0, (x, y, z))
