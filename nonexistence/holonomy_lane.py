"""No. 1 Holonomy Lane.

Eighteen rooms. Every one of them passes inspection on its own. The house is
drawn the way an architect draws: rooms sketched in place, doorways cut
through shared walls. Then three doorways are cut that no sketch can hold.

  I.   The stair hall climbs four storeys and arrives where it began.
  II.  The cloister turns five right angles around one square court.
  III. The hall is a quarter of an inch longer than the house beside it.

Holonomy is the mathematician's word for what goes wrong: carry a frame of
reference once around a loop and it comes back changed.
"""

from __future__ import annotations

from .building import Building, Door, Room, Stair, Window, WALL_NORMAL
from .geometry import Motion, ft, rot2

# ----------------------------------------------------------------------------
# Dimensions
# ----------------------------------------------------------------------------
WALL = ft(0, 6)          # interior partition
STOREY = 16 * ft(0, 7, 1)  # sixteen risers of 7¼″ = 9′-8″
RISER = ft(0, 7, 1)
TREAD = ft(0, 11)
FLIGHT_W = ft(4)
LANDING = ft(4)
FLIGHT_L = LANDING + 15 * TREAD          # 17′-9″
STAIR_S = FLIGHT_L + FLIGHT_W            # 21′-9″ outer square of the stair hall

GAL_L = ft(30)
GAL_W = ft(7)
GAL_S = GAL_L + GAL_W + WALL             # 37′-6″ outer square of the cloister


def world_rect(room: Room):
    m = room.hint
    pts = [m.apply((x, y, 0)) for x, y in ((0, 0), (room.w, 0), (0, room.d), (room.w, room.d))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def local_wall(room: Room, wx: int, wy: int):
    """Which local wall a world point on the room's boundary lies on, and where."""
    lx, ly, _ = room.hint.inv().apply((wx, wy, 0))
    if lx == 0:
        return "W", ly
    if lx == room.w:
        return "E", ly
    if ly == 0:
        return "S", lx
    if ly == room.d:
        return "N", lx
    raise ValueError(f"({wx},{wy}) is not on a wall of {room.key}")


class Draft:
    """The architect's sketch: rooms placed in a drawing, doors cut between them."""

    def __init__(self, b: Building):
        self.b = b
        self.n = 0

    def room(self, key, name, w, d, h, at=(0, 0, 0), r=0, **kw) -> Room:
        room = Room(key, name, w, d, h, hint=Motion(r, at), **kw)
        return self.b.add(room)

    def door(self, a: str, b: str, along: int, width=ft(3), kind="door", key=None,
             swing="in", hinge="L", note=""):
        """Cut a doorway through the wall shared by rooms a and b."""
        A, B = self.b.rooms[a], self.b.rooms[b]
        ax0, ay0, ax1, ay1 = world_rect(A)
        bx0, by0, bx1, by1 = world_rect(B)
        if ax1 <= bx0:
            pa, pb, t = (ax1, along), (bx0, along), bx0 - ax1
        elif bx1 <= ax0:
            pa, pb, t = (ax0, along), (bx1, along), ax0 - bx1
        elif ay1 <= by0:
            pa, pb, t = (along, ay1), (along, by0), by0 - ay1
        elif by1 <= ay0:
            pa, pb, t = (along, ay0), (along, by1), ay0 - by1
        else:
            raise ValueError(f"{a} and {b} overlap")
        wa, at_a = local_wall(A, *pa)
        wb, at_b = local_wall(B, *pb)
        self.n += 1
        k = key or f"D{self.n:02d}"
        A.add_door(Door(k, wa, at_a, 0, width, kind=kind, swing=swing, hinge=hinge))
        B.add_door(Door(k, wb, at_b, 0, width, kind=kind, swing="out" if swing == "in" else "in", hinge=hinge))
        self.b.glue(k, a, k, b, k, wall=t, note=note)
        return k


def build() -> Building:
    b = Building(
        name="No. 1 Holonomy Lane",
        address="1 Holonomy Lane · Charlotte, North Carolina",
    )
    D = Draft(b)

    # ---------------------------------------------------------------- south band
    D.room("LIB", "Library", ft(18), ft(25, 6), ft(11), at=(0, 0, 0), label="LIBRARY",
           windows=[Window("W", ft(8), ft(6)), Window("W", ft(18), ft(6)), Window("S", ft(9), ft(8))])
    D.room("DIN", "Dining Room", ft(16), ft(20), ft(10), at=(ft(18, 6), 0, 0), label="DINING",
           windows=[Window("S", ft(8), ft(8))])
    D.room("LIV", "Living Room", ft(22), ft(20), ft(10), at=(ft(35), 0, 0), label="LIVING",
           windows=[Window("S", ft(5), ft(6)), Window("S", ft(16), ft(10))])
    D.room("ENT", "Entrance Hall", ft(10), ft(25, 6), ft(12), at=(ft(57, 6), 0, 0), label="ENTRANCE HALL")
    D.room("KIT", "Kitchen", ft(16), ft(25, 6), ft(10), at=(ft(68), 0, 0), label="KITCHEN",
           windows=[Window("S", ft(8), ft(7)), Window("E", ft(13), ft(9))])

    # ---------------------------------------------------------------- the hall
    D.room("COR", "The Hall", ft(38, 6), ft(5), ft(9), at=(ft(18, 6), ft(20, 6), 0),
           kind="corridor", label="THE HALL")

    # ---------------------------------------------------------------- stair hall
    # Four flights in a pinwheel around an open well, climbing counter-clockwise.
    sx, sy = ft(38), ft(26)                       # south-west corner of the stair hall
    c = (sx + STAIR_S // 2, sy + STAIR_S // 2)    # centre of the well
    numerals = ["I", "II", "III", "IV"]
    for k in range(4):
        # Flight k is flight I turned k quarter-turns about the centre of the well.
        ox, oy = rot2(k, -STAIR_S // 2, -STAIR_S // 2)
        room = D.room(
            f"ST{k+1}", f"Stair Hall, Flight {numerals[k]}", FLIGHT_L, FLIGHT_W, STOREY + ft(9),
            at=(c[0] + ox, c[1] + oy, k * STOREY), r=k, kind="stair",
            label=f"FLIGHT {numerals[k]}",
            stair=Stair(x0=LANDING, risers=16, riser=RISER, tread=TREAD, width=FLIGHT_W),
            windows=([] if k == 0 else [Window("S", ft(2), ft(2, 6), sill=ft(0, 6), head=ft(9))])
                    + [Window("S", ft(11), ft(2, 6), sill=ft(4), head=ft(14))],
            note=f"Landing, Level {k+1}",
        )
        # Arrival from the previous flight onto this landing; departure from the top step.
        room.add_door(Door("in", "N", LANDING // 2, 0, FLIGHT_W, ft(8), kind="opening"))
        room.add_door(Door("out", "E", FLIGHT_W // 2, STOREY, FLIGHT_W, ft(8), kind="opening"))
    for k in range(4):
        a, nb = f"ST{k+1}", f"ST{(k+1) % 4 + 1}"
        b.glue(f"F{k+1}", a, "out", nb, "in", wall=0,
               note=f"Top of Flight {numerals[k]} onto the landing of Flight {numerals[(k+1) % 4]}")

    # ---------------------------------------------------------------- cloister
    # Five identical galleries, each turning right into the next, around one court.
    gc = (GAL_S // 2, ft(26) + GAL_S // 2)
    gnum = ["I", "II", "III", "IV", "V"]
    for k in range(5):
        # Gallery I walks west along the south side. Each next gallery is
        # gallery I turned a quarter-turn clockwise about the court's centre.
        base = Motion(2, (GAL_S // 2, -GAL_S // 2 + GAL_W, 0))
        spin = Motion(-k, (0, 0, 0))
        m = Motion(0, (gc[0], gc[1], 0)) @ spin @ base
        room = D.room(f"G{k+1}", f"Gallery {gnum[k]}", GAL_L, GAL_W, ft(10),
                      at=m.t, r=m.r, kind="gallery", label=f"GALLERY {gnum[k]}")
        room.add_door(Door("in", "S", GAL_W // 2, 0, ft(4), ft(8), kind="opening"))
        room.add_door(Door("out", "E", GAL_W // 2, 0, ft(4), ft(8), kind="opening"))
    for k in range(5):
        a, nb = f"G{k+1}", f"G{(k+1) % 5 + 1}"
        b.glue(f"C{k+1}", a, "out", nb, "in", wall=WALL,
               note=f"Gallery {gnum[k]} turns right into Gallery {gnum[(k+1) % 5]}")

    # ---------------------------------------------------------------- north wing
    D.room("BR1", "Bedroom I", ft(14, 6), ft(14), ft(10), at=(0, ft(64), 0), label="BEDROOM I",
           windows=[Window("N", ft(7, 3), ft(6)), Window("W", ft(7), ft(4))])
    D.room("BR2", "Bedroom II", ft(15), ft(14), ft(10), at=(ft(15), ft(64), 0), label="BEDROOM II",
           windows=[Window("N", ft(7, 6), ft(6))])
    D.room("BTH", "Bath", ft(10), ft(15, 3), ft(9), at=(ft(38), ft(48, 3), 0), label="BATH",
           windows=[Window("E", ft(8), ft(3), sill=ft(5))])

    # ---------------------------------------------------------------- doorways
    D.door("LIB", "DIN", ft(10))
    D.door("DIN", "LIV", ft(10), width=ft(5), kind="opening")
    D.door("LIV", "ENT", ft(10), width=ft(4), kind="opening")
    D.door("ENT", "KIT", ft(12))
    D.door("LIB", "COR", ft(23), kind="opening", width=ft(4))
    D.door("COR", "ENT", ft(23), kind="opening", width=ft(4), key="HALL")
    D.door("COR", "G1", ft(30), width=ft(4), kind="opening")
    D.door("COR", "ST1", sx + LANDING // 2, width=ft(3))
    D.door("LIB", "G2", ft(3, 6))
    D.door("G3", "BR1", ft(8))
    D.door("G3", "BR2", ft(22))
    D.door("BR1", "BR2", ft(71), width=ft(2, 10))
    D.door("G4", "BTH", ft(56))
    b.rooms["ENT"].add_door(Door("front", "S", ft(5), 0, ft(3, 6), kind="front"))

    # ---------------------------------------------------------------- the lies
    # III. The hall is lengthened by one quarter inch. Locally it is a perfectly
    # good hall; its east doorway simply sits ¼″ further along.
    b.rooms["COR"].w += 1
    # I.   Flight IV is glued to Flight I like every other pair. (Above.)
    # II.  Gallery V is glued to Gallery I like every other pair. (Above.)

    # The architect draws these three doorways last.
    b.seams = ["F4", "C5", "HALL"]
    return b
