#!/usr/bin/env python3
"""Adds a fresher "anchor" to the state constituency files: data/state_wk/<ID>.json gets wk[].a = what each Landtag constituency
looks like with the party geography of the 2025 federal election (FIRST votes by default: like wk[].s, the vote that decides the seat; data/firstvotes.json).

  python py/build_state_anchor.py            # NW SH NI (the next state elections)
  python py/build_state_anchor.py NW BY      # chosen states
  python py/build_state_anchor.py --all      # every state that has data/state_wk/<ID>.json + .geojson
  python py/build_state_anchor.py --second   # anchor on the federal SECOND votes (data/constituencies.json) instead of the first votes

Why: the last state election can be 4-5 years old and, for a party that has grown fast since (AfD: 5 % in the NRW election of 2022, 17 % in the federal
election of 2025), its old constituency pattern is a poor guide; a proportional swing multiplies every old quirk by 3-4.  The federal result of 2025 is the
freshest constituency-level result there is.  Backtest (py/calibrate_model.py data): predicting 2025 from a 2021 base misses by 1.15 points per party and
constituency, from a 2017 base by 1.76, and gets the leader right in 94 % vs 88 % of constituencies.

How: sample points inside every Landtag constituency, find the federal constituency each point lies in, and mix the federal shares with those
weights (first votes include candidate effects and independents; they go into Sonstige).  Only the national parties (CDU/CSU, SPD, AfD, Grüne, Linke, FDP, BSW) take the federal numbers; local parties (SSW, Freie Wähler, Bayernpartei ...)
keep the state-election number; federal parties the state file does not list go into Sonstige.  Rows are normalised to 100.
js/app.js blends the projection from this anchor with the one from the state-election result (config.json: stateAnchor = weight per state).
Needs numpy + matplotlib.
"""
import json, os, sys
import numpy as np
from matplotlib.path import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAND = {"BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin", "BB": "Brandenburg", "HE": "Hessen", "MV": "Mecklenburg-Vorpommern",
        "NI": "Niedersachsen", "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz", "SN": "Sachsen", "ST": "Sachsen-Anhalt",
        "SH": "Schleswig-Holstein", "TH": "Thüringen"}
NATIONAL = ["CDU/CSU", "SPD", "AfD", "Grüne", "Linke", "FDP", "BSW"]
GRID = 70   # sample points per side of a constituency's bounding box

def rings_of(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [Path(np.array(p[0])) for p in polys]            # outer rings only

def inside(paths, pts):
    m = np.zeros(len(pts), bool)
    for p in paths: m |= p.contains_points(pts)
    return m

def build(sid, fed, S, fparties):
    jp = os.path.join(HERE, "data", "state_wk", sid + ".json"); gp = os.path.join(HERE, "data", "state_wk", sid + ".geojson")
    D = json.load(open(jp, encoding="utf-8")); G = json.load(open(gp, encoding="utf-8"))
    byN = {int(f["properties"]["n"]): f for f in G["features"]}
    cand = [(n, rings_of(g)) for n, (land, g) in fed.items() if land == LAND[sid]]
    parties = D["parties"]; V = np.array([w.get("v") or 1 for w in D["wk"]], float); out = []; miss = []
    for w in D["wk"]:
        f = byN.get(int(w["n"]))
        if not f: miss.append(w["n"]); out.append(None); continue
        paths = rings_of(f["geometry"]); allp = np.vstack([p.vertices for p in paths])
        (x0, y0), (x1, y1) = allp.min(0), allp.max(0)
        gx, gy = np.meshgrid(np.linspace(x0, x1, GRID), np.linspace(y0, y1, GRID)); pts = np.c_[gx.ravel(), gy.ravel()]
        pts = pts[inside(paths, pts)]
        if len(pts) == 0: pts = allp.mean(0, keepdims=True)
        cnt = {}
        for n, pp in cand:
            c = int(inside(pp, pts).sum())
            if c: cnt[n] = c
        if not cnt: miss.append(w["n"]); out.append(None); continue
        tot = sum(cnt.values()); F = sum(S[n] * c for n, c in cnt.items()) / tot           # federal shares in fparties order
        fd = dict(zip(fparties, F)); a = []
        # federal parties that the state file does not list (BSW, Freie Wähler, federal Sonstige) go into Sonstige
        extra = fd.get("Sonstige", 0.0) + sum(v for p, v in fd.items() if p != "Sonstige" and p not in parties)
        for i, p in enumerate(parties):
            if p == "Sonstige": a.append(extra)
            elif p in NATIONAL and p in fd: a.append(fd[p])
            else: a.append(float(w["s"][i]))                                                 # local party (SSW, Freie Wähler ...): state-election number
        a = np.array(a, float); a = a / a.sum() * 100
        w["a"] = [round(float(v), 2) for v in a]; out.append(a)
    D["anchor"] = {"label": "2025 federal election (%s votes)" % ("second" if "--second" in sys.argv else "first"), "note": "see py/build_state_anchor.py"}
    open(jp, "w", encoding="utf-8", newline="").write(json.dumps(D, ensure_ascii=False, separators=(",", ":")))
    ok = [i for i, a in enumerate(out) if a is not None]
    A = np.array([out[i] for i in ok]); L = np.array([D["wk"][i]["s"] for i in ok]); v = V[ok]
    m = lambda X: (v[:, None] * X).sum(0) / v.sum()
    print(f"{sid}: {len(ok)}/{len(D['wk'])} constituencies anchored" + (f"  (no overlap: {miss})" if miss else ""))
    print("   party      " + "".join(f"{p[:7]:>9}" for p in parties))
    print("   2022 base  " + "".join(f"{x:9.1f}" for x in m(L)))
    print("   anchor     " + "".join(f"{x:9.1f}" for x in m(A)))

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ids = list(LAND) if "--all" in sys.argv else (args or ["NW", "SH", "NI"])
    C = json.load(open(os.path.join(HERE, "data", "constituencies.json"), encoding="utf-8")); fparties = C["parties"]
    S = {w["n"]: np.array(w["s"], float) for w in C["wk"]}
    if "--second" not in sys.argv:                             # first votes decide the seats, like the state files (wk[].s)
        FV = json.load(open(os.path.join(HERE, "data", "firstvotes.json"), encoding="utf-8")); fparties = FV["parties"]
        S = {int(n): np.array(v["f25"], float) for n, v in FV["wk"].items()}
    gj = json.load(open(os.path.join(HERE, "data", "wahlkreise.geojson"), encoding="utf-8"))
    land_of = {w["n"]: w["land"] for w in C["wk"]}
    fed = {int(f["properties"]["n"]): (land_of.get(int(f["properties"]["n"])), f["geometry"]) for f in gj["features"]}
    for sid in ids:
        if os.path.exists(os.path.join(HERE, "data", "state_wk", sid + ".json")):
            build(sid, fed, S, fparties)

if __name__ == "__main__":
    main()
