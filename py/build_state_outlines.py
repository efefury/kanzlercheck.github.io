#!/usr/bin/env python3
"""Adds "dk" to every state of data/germany-states.json: the state outline made from the federal constituencies
(data/wahlkreise.geojson), in the coordinates of the state map. The state picker (constituency level) uses it to clip the
constituencies and to draw the state borders, so borders and constituency edges come from one and the same geometry.
How: an edge that two constituencies share is walked in opposite directions and cancels out; what is left is the state outline.
Run:  python py/build_state_outlines.py
"""
import json, os, collections
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, B, C, D = 61.0036, -357.557, -97.3655, 5361.81      # lon/lat -> state map (same numbers as stPickDrawWk in js/app.js)
LAND = {"Baden-Württemberg":"BW","Bayern":"BY","Berlin":"BE","Brandenburg":"BB","Bremen":"HB","Hamburg":"HH","Hessen":"HE",
        "Mecklenburg-Vorpommern":"MV","Niedersachsen":"NI","Nordrhein-Westfalen":"NW","Rheinland-Pfalz":"RP","Saarland":"SL",
        "Sachsen":"SN","Sachsen-Anhalt":"ST","Schleswig-Holstein":"SH","Thüringen":"TH"}
q = lambda p: (round(p[0], 4), round(p[1], 4))

def rings(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        for i, r in enumerate(poly):
            yield [q(p) for p in r], i == 0

def outline(features):
    edges = collections.Counter()
    for f in features:
        for r, ext in rings(f["geometry"]):
            # make every ring run the same way (outer: counter-clockwise, hole: clockwise) so shared edges run in opposite directions
            area = sum(r[i][0]*r[i+1][1] - r[i+1][0]*r[i][1] for i in range(len(r)-1))
            if (area > 0) != ext: r = r[::-1]
            for a, b in zip(r, r[1:]):
                if a != b: edges[(a, b)] += 1
    for (a, b) in list(edges):
        rev = (b, a)
        if rev in edges and (a, b) in edges:
            n = min(edges[(a, b)], edges[rev]); edges[(a, b)] -= n; edges[rev] -= n
    left = [e for e, n in edges.items() if n > 0]
    nxt = collections.defaultdict(list)
    for (a, b), n in edges.items():
        for _ in range(max(n, 0)): nxt[a].append(b)
    out = []
    while nxt:
        a0 = next(iter(nxt)); ring = [a0]; a = a0
        while True:
            if not nxt.get(a): break
            b = nxt[a].pop()
            if not nxt[a]: del nxt[a]
            ring.append(b); a = b
            if a == a0: break
        if len(ring) > 3 and ring[0] == ring[-1]: out.append(ring)
    return out, left

def path(rs):
    return "".join("M" + "L".join("%.1f %.1f" % (A*x + B, C*y + D) for x, y in r[:-1]) + "Z" for r in rs)

w = json.load(open(os.path.join(HERE, "data", "wahlkreise.geojson"), encoding="utf-8"))
by = collections.defaultdict(list)
for f in w["features"]: by[LAND[f["properties"]["land"]]].append(f)
gp = os.path.join(HERE, "data", "germany-states.json")
g = json.load(open(gp, encoding="utf-8"))
EDGES = {}
for s in g["states"]:
    rs, left = outline(by[s["id"]])
    s["dk"] = path(rs)
    EDGES[s["id"]] = left
    print(s["id"], len(by[s["id"]]), "constituencies,", len(rs), "outline rings")

# "db": only the borders BETWEEN two states (an edge of one state outline that the neighbour walks the other way), chained into lines.
# Much lighter to draw than the full outlines (no coastline), so the map zooms and pans smoothly.
owner = {}
for sid, es in EDGES.items():
    for e in es: owner[e] = sid
adj = collections.defaultdict(set)
for (a, b), sid in owner.items():
    if (b, a) in owner and owner[(b, a)] != sid and a < b:
        adj[a].add(b); adj[b].add(a)
seen = set(); lines = []
def walk(a, b):
    line = [a, b]; seen.add(frozenset((a, b)))
    while len(adj[b]) == 2:
        c = [n for n in adj[b] if n != line[-2]][0]
        if frozenset((b, c)) in seen: break
        seen.add(frozenset((b, c))); line.append(c); b = c
    return line
for a in list(adj):                      # start at line ends / junctions first, then closed loops
    if len(adj[a]) != 2:
        for b in adj[a]:
            if frozenset((a, b)) not in seen: lines.append(walk(a, b))
for a in list(adj):
    for b in adj[a]:
        if frozenset((a, b)) not in seen: lines.append(walk(a, b))
def rdp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]; dx, dy = x2 - x1, y2 - y1; n = (dx*dx + dy*dy) ** .5 or 1e-9
    dm, im = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy*pts[i][0] - dx*pts[i][1] + x2*y1 - y2*x1) / n
        if d > dm: dm, im = d, i
    if dm <= eps: return [pts[0], pts[-1]]
    return rdp(pts[:im+1], eps)[:-1] + rdp(pts[im:], eps)
proj = lambda l: [(A*x + B, C*y + D) for x, y in l]
# "dbc": the same borders, coarser (about 0.35 map units); shown only while zooming / panning, the full "db" is shown at rest
g["dbc"] = "".join("M" + "L".join("%.1f %.1f" % pt for pt in rdp(proj(l), .35)) for l in lines)
g["db"] = "".join("M" + "L".join("%.1f %.1f" % (A*x + B, C*y + D) for x, y in l) for l in lines)
print("state borders:", len(lines), "lines,", len(g["db"]) // 1000, "KB, coarse", len(g["dbc"]) // 1000, "KB")
with open(gp, "w", encoding="utf-8") as fh: json.dump(g, fh, ensure_ascii=False, separators=(",", ":"))
