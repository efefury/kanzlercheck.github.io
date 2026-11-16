#!/usr/bin/env python3
"""Adds the state election BEFORE the last one to data/state_wk/<ID>.json (wk[].p), so the constituency projection can start from it as well.

  python py/add_prev_election.py NW nrw2017.csv --label 2017 --source "Landeswahlleiter NRW (final result 2017, first votes)"

nrw2017.csv: one row per constituency of the CURRENT map (same numbers n as in <ID>.json), first columns n [, name] [, voters], then one column per party in %
(decimal comma or point).  Party columns must be named like the parties in <ID>.json (CDU/CSU, SPD, AfD, Grüne, Linke, FDP, BSW, Freie Wähler, SSW ...);
columns the state file does not list are added to Sonstige.  Use the first vote (the one that decides the seat), as in the main file.
If the constituency boundaries changed, map the old results onto the new constituencies first (area-weighted is fine); every n must be there.

Then switch it on in config.json, e.g.   "stateBlend": {"NW": {"s": 0.2, "p": 0.2, "a": 0.6}}
  s = the last state election, p = the one before it (this file), a = the 2025 federal result (py/build_state_anchor.py).  The weights are normalised.
"""
import argparse, csv, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def num(x):
    x = (x or "").strip().replace("%", "").replace(" ", "")
    if not x: return 0.0
    return float(x.replace(",", ".")) if "," in x and "." not in x else float(x.replace(",", "")) if "," in x else float(x)

def main():
    a = argparse.ArgumentParser()
    a.add_argument("state"); a.add_argument("csv")
    a.add_argument("--label", default=""); a.add_argument("--source", default="")
    a.add_argument("--dir", default=os.path.join(HERE, "data", "state_wk"))
    o = a.parse_args()
    path = os.path.join(o.dir, o.state + ".json")
    D = json.load(open(path, encoding="utf-8")); parties = D["parties"]
    with open(o.csv, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096); f.seek(0)
        rows = list(csv.DictReader(f, delimiter=";" if sample.count(";") > sample.count(",") else ","))
    cols = [c for c in rows[0] if c and c.strip().lower() not in ("n", "nr", "name", "voters", "wahlberechtigte")]
    known = [c for c in cols if c in parties]; extra = [c for c in cols if c not in parties and c != "Sonstige"]
    byn = {int(float(r["n"])): r for r in rows}
    miss = [w["n"] for w in D["wk"] if int(w["n"]) not in byn]
    if miss: sys.exit(f"missing constituencies in the CSV: {miss}")
    for w in D["wk"]:
        r = byn[int(w["n"])]; v = []
        for p in parties:
            x = num(r.get(p)) if p in known else 0.0
            if p == "Sonstige": x = num(r.get("Sonstige")) + sum(num(r.get(c)) for c in extra)
            v.append(x)
        t = sum(v)
        if t <= 0: sys.exit(f"constituency {w['n']}: no results")
        w["p"] = [round(x / t * 100, 2) for x in v]
    D["prevLabel"] = o.label; D["prevSource"] = o.source
    open(path, "w", encoding="utf-8", newline="").write(json.dumps(D, ensure_ascii=False, separators=(",", ":")))
    print(f"{o.state}: added the previous election ({o.label or 'no label'}) to {len(D['wk'])} constituencies")
    if extra: print("  added to Sonstige:", ", ".join(extra))
    unused = [p for p in parties if p not in known and p != "Sonstige"]
    if unused: print("  no column for:", ", ".join(unused), "(set to 0)")

if __name__ == "__main__":
    main()
