#!/usr/bin/env python3
"""Builds data/state_wk/<ID>.json + <ID>.geojson (the constituency map of a state page) from a results CSV and a boundaries GeoJSON.

  python py/build_state_wk.py BW results.csv boundaries.geojson [--n-field WKR_NR] [--name-field WKR_NAME] [--label 2026] [--source "..."]

results.csv: columns n, name, optional voters, then one column per party (percent; decimal comma or point). Party names = the
column headers of state_polls/<State>.csv; put the rest in "Sonstige". Format details: data/state_wk/README.md
"""
import argparse, csv, json, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def num(s):
    s = (s or "").strip().replace("%", "").replace(" ", "")
    if not s: return 0.0
    return float(s.replace(",", ".")) if "," in s and "." not in s else float(s.replace(",", "")) if "," in s else float(s)

def rnd(c):
    return [round(c[0], 4), round(c[1], 4)] if isinstance(c[0], (int, float)) else [rnd(x) for x in c]

def main():
    a = argparse.ArgumentParser()
    a.add_argument("state"); a.add_argument("csv"); a.add_argument("geojson")
    a.add_argument("--n-field", default="n"); a.add_argument("--name-field", default="name")
    a.add_argument("--label", default=""); a.add_argument("--source", default="")
    o = a.parse_args()
    with open(o.csv, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096); f.seek(0)
        dl = ";" if sample.count(";") > sample.count(",") else ","
        rows = list(csv.DictReader(f, delimiter=dl))
    meta = {"n", "name", "voters", "v"}
    parties = [k for k in rows[0].keys() if k and k.strip().lower() not in meta]
    wk = []
    for r in rows:
        low = {k.strip().lower(): v for k, v in r.items() if k}
        w = {"n": int(float(low["n"])), "name": (low.get("name") or "").strip()}
        v = low.get("voters") or low.get("v")
        if v: w["v"] = int(num(v))
        w["s"] = [round(num(r[p]), 2) for p in parties]
        wk.append(w)
    out = {"parties": parties, "wk": wk}
    if o.label: out["label"] = o.label
    if o.source: out["source"] = o.source
    with open(o.geojson, encoding="utf-8") as f: g = json.load(f)
    feats = []
    for ft in g["features"]:
        p = ft.get("properties") or {}
        if o.n_field not in p: continue
        geo = ft["geometry"]
        feats.append({"type": "Feature", "properties": {"n": int(float(p[o.n_field])), "name": str(p.get(o.name_field, ""))},
                      "geometry": {"type": geo["type"], "coordinates": rnd(geo["coordinates"])}})
    have = {w["n"] for w in wk}; got = {f["properties"]["n"] for f in feats}
    if have - got: print("warning: no boundary for constituencies", sorted(have - got))
    if got - have: print("warning: no results for constituencies", sorted(got - have))
    d = os.path.join(HERE, "data", "state_wk"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, o.state + ".json"), "w", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(d, o.state + ".geojson"), "w", encoding="utf-8") as f: json.dump({"type": "FeatureCollection", "features": feats}, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote data/state_wk/%s.json (%d constituencies, %d parties) and %s.geojson (%d shapes)" % (o.state, len(wk), len(parties), o.state, len(feats)))

if __name__ == "__main__":
    main()
