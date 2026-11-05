"""Rooms, doors, and the gluings between them.

A building here is not a set of coordinates. It is a list of rooms, each
described only in its own local frame, and a list of doorways that say which
wall of one room meets which wall of another. Whether the rooms can all be
placed in one ordinary space is a question to be answered, not assumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import FOOT, INCH, Motion, HALF_TURN, translate, ft, fmt_len, fmt_inches

# Outward normal of each wall, as a quarter-turn index (0 = +x).
WALL_NORMAL = {"E": 0, "N": 1, "W": 2, "S": 3}


@dataclass
class Door:
    key: str
    wall: str            # N / E / S / W of the room's local frame
    at: int              # centre, measured along the wall from the room's origin
    z: int = 0           # sill height in the room's local frame
    width: int = ft(3)
    height: int = ft(6, 8)
    kind: str = "door"   # "door" (with a leaf), "opening", or "front" (exterior)
    swing: str = "in"    # for the drawing: which side the leaf swings to
    hinge: str = "L"


@dataclass
class Window:
    wall: str
    at: int
    width: int
    sill: int = ft(2, 6)
    head: int = ft(8)


@dataclass
class Stair:
    """A straight flight climbing in +x of the room's local frame."""
    x0: int              # where the first riser is
    risers: int
    riser: int
    tread: int
    width: int
    y0: int = 0

    @property
    def rise(self) -> int:
        return self.risers * self.riser

    @property
    def run(self) -> int:
        return (self.risers - 1) * self.tread


@dataclass
class Room:
    key: str
    name: str
    w: int               # local x extent (clear)
    d: int               # local y extent (clear)
    h: int               # ceiling height above the lowest floor
    kind: str = "room"
    doors: dict[str, Door] = field(default_factory=dict)
    windows: list[Window] = field(default_factory=list)
    stair: Stair | None = None
    label: str = ""      # short name for the drawing
    note: str = ""
    hint: Motion | None = None   # where the architect first sketched it

    def add_door(self, door: Door) -> Door:
        self.doors[door.key] = door
        return door

    def door_frame(self, key: str) -> Motion:
        """Frame at the centre of a doorway on the wall face: local x = outward normal."""
        d = self.doors[key]
        n = WALL_NORMAL[d.wall]
        if d.wall == "E":
            c = (self.w, d.at, d.z)
        elif d.wall == "W":
            c = (0, d.at, d.z)
        elif d.wall == "N":
            c = (d.at, self.d, d.z)
        else:
            c = (d.at, 0, d.z)
        return Motion(n, c)

    def wall_length(self, wall: str) -> int:
        return self.d if wall in ("E", "W") else self.w


@dataclass
class Gluing:
    """Doorway `da` of room `a` opens onto doorway `db` of room `b`."""
    key: str
    a: str
    da: str
    b: str
    db: str
    wall: int = ft(0, 6)   # thickness of the wall the doorway passes through
    note: str = ""


@dataclass
class Building:
    name: str
    address: str
    rooms: dict[str, Room] = field(default_factory=dict)
    gluings: list[Gluing] = field(default_factory=list)
    seams: list[str] = field(default_factory=list)   # gluings the architect drew last

    def add(self, room: Room) -> Room:
        self.rooms[room.key] = room
        return room

    def glue(self, key, a, da, b, db, wall=ft(0, 6), note="") -> Gluing:
        g = Gluing(key, a, da, b, db, wall, note)
        self.gluings.append(g)
        return g

    def gluing(self, key: str) -> Gluing:
        return next(g for g in self.gluings if g.key == key)

    def transform(self, g: Gluing, forward: bool = True) -> Motion:
        """The motion carrying room a's frame to room b's frame across the doorway."""
        A, B = self.rooms[g.a], self.rooms[g.b]
        T = A.door_frame(g.da) @ translate(g.wall) @ HALF_TURN @ B.door_frame(g.db).inv()
        return T if forward else T.inv()


# --------------------------------------------------------------------------
# Local inspection: every room, on its own, must be a legal room.
# Figures are from the International Residential Code (IRC).
# --------------------------------------------------------------------------

CODE = {
    "ceiling": (ft(7), "R305.1", "Ceiling height, habitable space", "≥ 7′-0″"),
    "door_w": (ft(2, 8), "R311.2", "Egress door clear width", "≥ 32″"),
    "door_h": (ft(6, 8), "R311.2", "Egress door clear height", "≥ 6′-8″"),
    "stair_w": (ft(3), "R311.7.1", "Stair width", "≥ 36″"),
    "riser": (ft(0, 7, 3), "R311.7.5.1", "Riser height", "≤ 7¾″"),
    "tread": (ft(0, 10), "R311.7.5.2", "Tread depth", "≥ 10″"),
    "headroom": (ft(6, 8), "R311.7.2", "Stair headroom", "≥ 6′-8″"),
    "hall_w": (ft(3), "R311.6", "Hallway width", "≥ 3′-0″"),
}


@dataclass
class Finding:
    room: str
    item: str
    section: str
    required: str
    found: str
    ok: bool


def inspect_room(room: Room) -> list[Finding]:
    out: list[Finding] = []

    def add(item, found, ok):
        _, sec, label, req = CODE[item]
        out.append(Finding(room.key, label, sec, req, found, ok))

    if room.kind != "stair":
        add("ceiling", fmt_len(room.h), room.h >= CODE["ceiling"][0])
    if room.kind in ("corridor", "gallery"):
        add("hall_w", fmt_len(min(room.w, room.d)), min(room.w, room.d) >= CODE["hall_w"][0])

    for d in room.doors.values():
        # The doorway must lie wholly on its wall.
        L = room.wall_length(d.wall)
        on_wall = d.width // 2 <= d.at <= L - d.width // 2
        if not on_wall:
            out.append(Finding(room.key, f"Doorway {d.key} on wall", "—", "on wall", "off wall", False))
        if d.kind != "opening":
            add("door_w", fmt_inches(d.width), d.width >= CODE["door_w"][0])
            add("door_h", fmt_len(d.height), d.height >= CODE["door_h"][0])

    s = room.stair
    if s:
        add("riser", fmt_inches(s.riser), s.riser <= CODE["riser"][0])
        add("tread", fmt_inches(s.tread), s.tread >= CODE["tread"][0])
        add("stair_w", fmt_len(s.width), s.width >= CODE["stair_w"][0])
        clear = room.h - s.rise
        add("headroom", fmt_len(clear), clear >= CODE["headroom"][0])
        fits = s.x0 + s.run <= room.w
        if not fits:
            out.append(Finding(room.key, "Flight fits room", "—", "fits", "overruns", False))
    return out


def inspect_gluing(b: Building, g: Gluing) -> list[Finding]:
    A, B = b.rooms[g.a], b.rooms[g.b]
    da, db = A.doors[g.da], B.doors[g.db]
    ok = da.width == db.width and da.height == db.height
    return [Finding(g.key, "Doorway leaves match", "—", "equal", f"{fmt_inches(da.width)} / {fmt_inches(db.width)}", ok)]


def inspect(b: Building) -> list[Finding]:
    out = []
    for r in b.rooms.values():
        out += inspect_room(r)
    for g in b.gluings:
        out += inspect_gluing(b, g)
    return out
