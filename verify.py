#!/usr/bin/env python3
"""Check a Certificate of Nonexistence by hand, without a solver.

    python3 verify.py out/proof/building.json out/proof/certificate.json

Uses only the Python standard library and whole-number arithmetic. It reads the
rooms exactly as each room describes itself, walks each loop named on the
certificate, and multiplies the doorway transformations together. A building
that exists must bring every loop back to the identity. This one does not.
"""

import hashlib
import json
import sys

NORMAL = {"E": 0, "N": 1, "W": 2, "S": 3}
ROT = [((1, 0), (0, 1)), ((0, -1), (1, 0)), ((-1, 0), (0, -1)), ((0, 1), (-1, 0))]


def rot(r, x, y):
    (a, b), (c, d) = ROT[r % 4]
    return a * x + b * y, c * x + d * y


def compose(m, n):
    """(r, (x, y, z)) means: turn r quarter-turns, then move by (x, y, z)."""
    x, y = rot(m[0], n[1][0], n[1][1])
    return ((m[0] + n[0]) % 4, (x + m[1][0], y + m[1][1], n[1][2] + m[1][2]))


def inverse(m):
    x, y = rot(-m[0], -m[1][0], -m[1][1])
    return ((-m[0]) % 4, (x, y, -m[1][2]))


def door_frame(room, key):
    d = room["doors"][key]
    w, depth = room["w"], room["d"]
    centre = {"E": (w, d["at"]), "W": (0, d["at"]), "N": (d["at"], depth), "S": (d["at"], 0)}[d["wall"]]
    return (NORMAL[d["wall"]], (centre[0], centre[1], d["z"]))


def crossing(spec, doorway, forward):
    A, B = spec["rooms"][doorway["a"]], spec["rooms"][doorway["b"]]
    T = door_frame(A, doorway["door_a"])
    T = compose(T, (0, (doorway["wall"], 0, 0)))      # through the wall
    T = compose(T, (2, (0, 0, 0)))                     # turn round to face back
    T = compose(T, inverse(door_frame(B, doorway["door_b"])))
    return T if forward else inverse(T)


def feet(u):
    s = "-" if u < 0 else ""
    u = abs(u)
    f, r = divmod(u, 48)
    i, q = divmod(r, 4)
    return f"{s}{f}'-{i}{['', ' 1/4', ' 1/2', ' 3/4'][q]}\""


def main(spec_path, cert_path):
    spec = json.load(open(spec_path))
    cert = json.load(open(cert_path))
    canon = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    h = hashlib.sha256(canon).hexdigest()
    print(f"building     {spec['name']}")
    print(f"sha-256      {h}")
    print(f"certificate  {cert['sha256']}")
    if h != cert["sha256"]:
        print("MISMATCH: this certificate was issued for a different building.")
        return 2
    doorways = {d["key"]: d for d in spec["doorways"]}
    failed = 0
    for loop in cert["loops"]:
        here = loop["loop"][0][0]
        acc = (0, (0, 0, 0))
        print(f"\nloop through doorway {loop['seam']}:")
        for (a, key, b) in loop["loop"]:
            d = doorways[key]
            assert here == a and {a, b} == {d["a"], d["b"]}, "the walk is broken"
            acc = compose(acc, crossing(spec, d, d["a"] == a))
            print(f"   {a:>4} -> {b:<4} through {key:<5} running total: "
                  f"{acc[0] * 90:>3} deg, ({feet(acc[1][0])}, {feet(acc[1][1])}, {feet(acc[1][2])})")
            here = b
        assert here == loop["loop"][0][0], "the walk does not come home"
        closes = acc == (0, (0, 0, 0))
        print("   comes home unchanged" if closes else "   comes home CHANGED: no placement of these rooms exists")
        failed += not closes
    print()
    if failed:
        print(f"{failed} loop(s) fail to close. The building cannot exist in Euclidean space.")
        return 0
    print("Every loop closes. This certificate proves nothing.")
    return 1


if __name__ == "__main__":
    args = sys.argv[1:] or ["out/proof/building.json", "out/proof/certificate.json"]
    sys.exit(main(*args))
