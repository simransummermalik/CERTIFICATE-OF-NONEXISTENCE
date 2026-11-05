"""Inspect a building for existence.

The question put to the solver: is there any way to place every room in one
ordinary three-dimensional space, each turned only by whole quarter-turns and
moved by whole quarter-inches, so that every doorway lines up with its partner?

If the answer is no, the solver returns a proof, and the smallest set of
doorways that the proof needs.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import time
from collections import deque
from pathlib import Path

import z3

# Proof objects must be switched on before the solver's context exists.
z3.set_param(proof=True)

from .building import Building, inspect
from .geometry import IDENTITY, Motion, fmt_len


# ---------------------------------------------------------------------------
# Canonical description: only what each room knows about itself.
# ---------------------------------------------------------------------------

def spec(b: Building) -> dict:
    rooms = {}
    for k, r in sorted(b.rooms.items()):
        rooms[k] = {
            "name": r.name, "kind": r.kind, "w": r.w, "d": r.d, "h": r.h,
            "doors": {dk: {"wall": d.wall, "at": d.at, "z": d.z, "width": d.width,
                           "height": d.height, "kind": d.kind}
                      for dk, d in sorted(r.doors.items())},
            "stair": None if not r.stair else {
                "x0": r.stair.x0, "risers": r.stair.risers, "riser": r.stair.riser,
                "tread": r.stair.tread, "width": r.stair.width},
        }
    glu = [{"key": g.key, "a": g.a, "door_a": g.da, "b": g.b, "door_b": g.db, "wall": g.wall}
           for g in b.gluings]
    return {"name": b.name, "unit": "quarter inch", "rooms": rooms, "doorways": glu}


def digest(s: dict) -> str:
    raw = json.dumps(s, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# The architect's drawing: place rooms along a spanning tree.
# ---------------------------------------------------------------------------

def layout(b: Building, root: str = "ENT", avoid=()):
    """Breadth-first placement from the front door. Doorways in `avoid` are used last."""
    adj = {k: [] for k in b.rooms}
    for g in b.gluings:
        adj[g.a].append((g, True))
        adj[g.b].append((g, False))
    pose = {root: b.rooms[root].hint or IDENTITY}
    parent = {root: None}
    tree = set()
    q = deque([root])
    while q:
        u = q.popleft()
        for g, fwd in sorted(adj[u], key=lambda e: (e[0].key in avoid, e[0].key)):
            v = g.b if fwd else g.a
            if v in pose or g.key in avoid:
                continue
            pose[v] = pose[u] @ b.transform(g, fwd)
            parent[v] = (u, g.key)
            tree.add(g.key)
            q.append(v)
    # Anything reachable only through an avoided doorway.
    for g in b.gluings:
        for (u, v, fwd) in ((g.a, g.b, True), (g.b, g.a, False)):
            if u in pose and v not in pose:
                pose[v] = pose[u] @ b.transform(g, fwd)
                parent[v] = (u, g.key)
                tree.add(g.key)
    return pose, parent, tree


def tree_path(parent, u):
    out = []
    while parent[u] is not None:
        p, gk = parent[u]
        out.append((p, gk, u))
        u = p
    return out[::-1]


def defects(b: Building, pose, parent, tree):
    """Every doorway left out of the tree closes a loop. Measure what the loop does."""
    found = []
    for g in b.gluings:
        if g.key in tree:
            continue
        hol = pose[g.a] @ b.transform(g) @ pose[g.b].inv()   # loop based at the front door
        # The loop: tree path to a, across g, tree path back from b.
        pa, pb = tree_path(parent, g.a), tree_path(parent, g.b)
        i = 0
        while i < min(len(pa), len(pb)) and pa[i] == pb[i]:
            i += 1
        down = pa[i:]
        up = pb[i:]
        steps = []                         # (from, doorway, to)
        start = down[0][0] if down else (up[0][0] if up else g.a)
        for (u, gk, v) in down:
            steps.append((u, gk, v))
        steps.append((g.a, g.key, g.b))
        for (u, gk, v) in reversed(up):
            steps.append((v, gk, u))
        # Holonomy based at the loop's own first room.
        acc = IDENTITY
        for (u, gk, v) in steps:
            gg = b.gluing(gk)
            acc = acc @ b.transform(gg, gg.a == u)
        found.append({
            "doorway": g.key, "holonomy_at_front_door": hol,
            "loop": steps, "base": start, "holonomy": acc,
            "closes": acc.is_identity,
        })
    return found


def shortest_loop(b: Building, seam: str, pose) -> dict:
    """The shortest walk that crosses `seam` once and comes home."""
    g = b.gluing(seam)
    adj = {k: [] for k in b.rooms}
    for h in b.gluings:
        if h.key == seam:
            continue
        adj[h.a].append((h.key, h.b))
        adj[h.b].append((h.key, h.a))
    prev = {g.b: None}
    q = deque([g.b])
    while q:
        u = q.popleft()
        for hk, v in sorted(adj[u]):
            if v not in prev:
                prev[v] = (u, hk)
                q.append(v)
    path, u = [], g.a
    while prev[u] is not None:
        p, hk = prev[u]
        path.append((p, hk, u))
        u = p
    steps = path[::-1] + [(g.a, g.key, g.b)]
    acc, rows = IDENTITY, []
    for (u, hk, v) in steps:
        h = b.gluing(hk)
        T = b.transform(h, h.a == u)
        acc = acc @ T
        rows.append({"from": u, "doorway": hk, "to": v,
                     "step": {"turns": T.r, "t": list(T.t)},
                     "so_far": {"turns": acc.r, "t": list(acc.t)}})
    base = g.b
    world = pose[base] @ acc @ pose[base].inv()
    fp = world.fixed_point()
    return {
        "seam": seam, "base": base, "loop": [list(st) for st in steps], "steps": rows,
        "holonomy": {"turns": acc.r, "t": list(acc.t), "text": acc.describe()},
        "world": {"turns": world.r, "t": list(world.t),
                  "pivot": None if fp is None else [str(fp[0]), str(fp[1])]},
    }


# ---------------------------------------------------------------------------
# The solver.
# ---------------------------------------------------------------------------

def _rot(r, vx, vy):
    x = z3.If(r == 0, vx, z3.If(r == 1, -vy, z3.If(r == 2, -vx, vy)))
    y = z3.If(r == 0, vy, z3.If(r == 1, vx, z3.If(r == 2, -vy, -vx)))
    return x, y


def encode(b: Building, keys, solver, track=True):
    P = {}
    for k in sorted(b.rooms):
        r, x, y, zz = z3.Ints(f"{k}.turn {k}.x {k}.y {k}.z")
        P[k] = (r, x, y, zz)
        solver.add(r >= 0, r <= 3)
    tags = {}
    for g in b.gluings:
        if g.key not in keys:
            continue
        T = b.transform(g)
        ra, xa, ya, za = P[g.a]
        rb, xb, yb, zb = P[g.b]
        dx, dy = _rot(ra, T.t[0], T.t[1])
        c = z3.And(rb == (ra + T.r) % 4, xb == xa + dx, yb == ya + dy, zb == za + T.t[2])
        if track:
            tag = z3.Bool(f"doorway {g.key}")
            solver.assert_and_track(c, tag)
            tags[str(tag)] = g.key
        else:
            solver.add(c)
    return P, tags


def exists(b: Building, keys) -> bool:
    s = z3.Solver()
    encode(b, set(keys), s, track=False)
    return s.check() == z3.sat


def inspect_existence(b: Building, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    all_keys = {g.key for g in b.gluings}
    t0 = time.perf_counter()

    # 1. The whole house.
    z3.set_param("smt.core.minimize", True)
    s = z3.Solver()
    P, tags = encode(b, all_keys, s)
    verdict = s.check()
    core = sorted(tags[str(c)] for c in s.unsat_core()) if verdict == z3.unsat else []
    t1 = time.perf_counter()

    # 2. A full proof object, for the record.
    sp = z3.Solver()
    encode(b, all_keys, sp, track=False)
    assert sp.check() == z3.unsat
    proof_text = str(sp.proof())
    (out_dir / "z3_proof.txt").write_text(proof_text)

    # 3. With the three seams bricked up, the house exists. Ask for coordinates.
    s2 = z3.Solver()
    P2, _ = encode(b, all_keys - set(b.seams), s2, track=False)
    s2.add(*[v == 0 for v in P2["ENT"]])
    assert s2.check() == z3.sat
    m = s2.model()
    placement = {k: [m[v].as_long() for v in vs] for k, vs in P2.items()}

    # 4. Each seam on its own is fatal.
    alone = {sk: exists(b, (all_keys - set(b.seams)) | {sk}) for sk in b.seams}

    # 5. How few doorways would have to be bricked up? Try every pair, then every triple.
    keys = sorted(all_keys)
    pairs = [p for p in itertools.combinations(keys, 2) if exists(b, all_keys - set(p))]
    triples = [t for t in itertools.combinations(keys, 3) if exists(b, all_keys - set(t))]
    singles = [k for k in keys if exists(b, all_keys - {k})]
    t2 = time.perf_counter()

    # 6. The architect's drawing, and the loops it cannot close.
    pose, parent, tree = layout(b, avoid=b.seams)
    chords = defects(b, pose, parent, tree)
    loops = [shortest_loop(b, sk, pose) for sk in b.seams]
    for L in loops:
        ks = {gk for (_, gk, _) in L["loop"]}
        s3 = z3.Solver()
        _, tg = encode(b, ks, s3)
        L["solver"] = str(s3.check())
        L["core"] = sorted(tg[str(c)] for c in s3.unsat_core()) if L["solver"] == "unsat" else []

    findings = inspect(b)
    result = {
        "building": b.name,
        "address": b.address,
        "sha256": digest(spec(b)),
        "z3_version": z3.get_version_string(),
        "rooms": len(b.rooms),
        "doorways": len(b.gluings),
        "local_checks": len(findings),
        "local_failures": [f.__dict__ for f in findings if not f.ok],
        "verdict": str(verdict),
        "core": core,
        "seconds_main": round(t1 - t0, 4),
        "seconds_total": round(t2 - t0, 3),
        "proof_chars": len(proof_text),
        "proof_lines": proof_text.count("\n") + 1,
        "seams": b.seams,
        "seam_alone_exists": alone,
        "exists_without_seams": True,
        "fixes_one": singles,
        "fixes_two": [list(p) for p in pairs],
        "fixes_three": [list(t) for t in triples],
        "triples_tried": len(list(itertools.combinations(keys, 3))),
        "placement_without_seams": placement,
        "loops": loops,
        "loops_that_close": [c["doorway"] for c in chords if c["closes"]],
        "drawing": {k: {"turns": m.r, "t": list(m.t)} for k, m in pose.items()},
        "drawing_tree": sorted(tree),
    }
    (out_dir / "certificate.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    (out_dir / "building.json").write_text(json.dumps(spec(b), indent=1, ensure_ascii=False))
    return result


if __name__ == "__main__":
    from .holonomy_lane import build
    r = inspect_existence(build(), Path(__file__).resolve().parent.parent / "out" / "proof")
    print(json.dumps({k: v for k, v in r.items() if k not in ("placement_without_seams", "fixes_three")},
                     indent=1, ensure_ascii=False)[:6000])
    print("triples that make the house exist:", len(r["fixes_three"]), "of", r["triples_tried"])
