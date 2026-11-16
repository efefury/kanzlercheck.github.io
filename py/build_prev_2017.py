#!/usr/bin/env python3
"""Builds the 2017 state-election inputs for py/add_prev_election.py (NW and SH) from the official results files.

  python py/build_prev_2017.py NW  LW17_WK_insgesamt.txt        # IT.NRW final result 2017, constituency level
  python py/build_prev_2017.py SH  ergebnis-download.csv        # Statistikamt Nord final result 2017, polling-district level

Each call writes data/state_wk/prev/<ID>2017.csv (first votes in %, one row per constituency of the CURRENT map, columns = the parties of
data/state_wk/<ID>.json) and then runs add_prev_election.py, which stores them as wk[].p.  Switch it on in config.json -> stateBlend.

Both use the FIRST vote (the one that decides the seat), like wk[].s.  A party without a constituency candidate gets its second-vote share
times its typical first/second ratio in the constituencies where it did run (so e.g. SSW outside the north is not 0).

NW: the 2022 map has other constituency boundaries than 2017 (128 constituencies both times, but numbering and some cuts changed).  Without the 2017 boundaries
a proper overlay is not possible, so every current constituency is mapped by NAME to its 2017 namesake; where the current constituency is a merger or a
new cut, MIX below says which 2017 constituencies it is made of and with what weight (an estimate, listed there so it can be corrected).
SH: the 35 constituencies are the same as in 2022 (checked by municipality codes and names); the polling districts are summed per constituency.
"""
import csv, json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREV = os.path.join(HERE, "data", "state_wk", "prev")

def dash(s): return s.replace(" - ", " – ").strip()

def share_fill(rows, parties):
    """rows: list of dict party -> (first_count|None, second_count), plus '_v1', '_v2' valid totals.  Returns list of {party: pct} incl. Sonstige."""
    ratio = {}
    for p in parties:
        a = sum(r[p][0] for r in rows if r[p][0]); b = sum(r[p][1] for r in rows if r[p][0])
        v1 = sum(r["_v1"] for r in rows if r[p][0]); v2 = sum(r["_v2"] for r in rows if r[p][0])
        ratio[p] = (a / v1) / (b / v2) if a and b else 0.0
    out = []
    for r in rows:
        sh = {}; known = 0.0
        for p in parties:
            f, s = r[p]
            if f: sh[p] = f / r["_v1"]; known += sh[p]
            else: sh[p] = ratio[p] * s / r["_v2"]
        sh["Sonstige"] = max(0.0, 1 - known)
        t = sum(sh.values()); out.append({k: v / t * 100 for k, v in sh.items()})
    return out

def write(sid, out):
    os.makedirs(PREV, exist_ok=True)
    D = json.load(open(os.path.join(HERE, "data", "state_wk", sid + ".json"), encoding="utf-8")); parties = D["parties"]
    path = os.path.join(PREV, sid + "2017.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["n", "name"] + parties)
        for wk, r in zip(D["wk"], out): w.writerow([wk["n"], wk["name"]] + [f"{r.get(p, 0.0):.2f}" for p in parties])
    return path

def nw(src):
    lines = open(src, encoding="utf-8-sig").read().splitlines(); hdr = lines[2].split(";")
    ix = {h: i for i, h in enumerate(hdr)}
    def num(x): return int(x) if x.strip() else None
    cols = {"CDU/CSU": "CDU", "SPD": "SPD", "AfD": "AfD", "Grüne": "GRÜNE", "Linke": "DIE LINKE", "FDP": "FDP"}
    res = {}
    for l in lines[4:]:
        c = l.split(";")
        if len(c) < 10 or not c[0].strip(): continue
        r = {"_v1": num(c[ix["Gültige Stimmen Erststimmen"]]), "_v2": num(c[ix["Gültige Stimmen Zweitstimmen"]])}
        for p, h in cols.items(): r[p] = (num(c[ix[h + " Erststimmen"]]), num(c[ix[h + " Zweitstimmen"]]) or 0)
        res[dash(c[1])] = r
    names = list(res); parties = list(cols)
    pct = dict(zip(names, share_fill([res[n] for n in names], parties)))
    D = json.load(open(os.path.join(HERE, "data", "state_wk", "NW.json"), encoding="utf-8"))
    R = lambda *a: [(x, 1 / len(a)) for x in a]
    reckl = ["Recklinghausen " + x for x in ("I", "II", "III", "IV", "V")]
    MIX = {  # current constituency -> [(2017 constituency, weight)]
        "Rhein-Sieg-Kreis III - Euskirchen III": [("Rhein-Sieg-Kreis III", 1)],
        "Rhein-Sieg-Kreis V": R("Rhein-Sieg-Kreis I", "Rhein-Sieg-Kreis II", "Rhein-Sieg-Kreis III", "Rhein-Sieg-Kreis IV"),   # new cut, no 2017 namesake
        "Remscheid I - Oberbergischer Kreis III": [("Remscheid – Oberbergischer Kreis III", 1)],
        "Mettmann III - Mülheim II": [("Mettmann III", .75), ("Essen I – Mülheim II", .25)],
        "Essen I": [("Essen I – Mülheim II", 1)],
        "Gelsenkirchen I - Recklinghausen V": [("Gelsenkirchen I", .6), ("Recklinghausen V", .4)],
        "Bottrop - Recklinghausen VI": [("Bottrop", .7)] + [(n, .06) for n in reckl],
        "Münster I - Steinfurt IV": [("Münster I", .75), ("Steinfurt III", .25)],
        "Münster III - Coesfeld III": [("Münster I", .35), ("Münster II", .35), ("Coesfeld II", .3)],
        "Herford I": [("Herford I – Minden-Lübbecke III", 1)],
        "Herford II - Minden-Lübbecke III": [("Herford II – Minden-Lübbecke IV", 1)],
        "Lippe II - Herford III": [("Lippe II", .7), ("Herford II – Minden-Lübbecke IV", .3)],
        "Bochum III": [("Bochum III – Herne II", 1)],
        "Herne": [("Herne I", .65), ("Bochum III – Herne II", .35)],
    }
    out, used = [], set()
    for w in D["wk"]:
        m = MIX.get(w["name"]) or [(dash(w["name"]), 1)]
        row = {}
        for n, wt in m:
            if n not in pct: sys.exit(f"no 2017 constituency called {n!r} (for {w['name']!r})")
            used.add(n)
            for p, v in pct[n].items(): row[p] = row.get(p, 0) + wt * v
        t = sum(m_[1] for m_ in m); out.append({p: v / t for p, v in row.items()})
    print("NW: 2017 constituencies not used on their own:", ", ".join(n for n in names if n not in used) or "-")
    return out

def sh(src):
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig", newline=""), delimiter=";"))
    num = lambda x: int(x) if (x or "").strip() else 0
    # column order of the file = ballot order 2017: CDU SPD GRÜNE FDP PIRATEN SSW LINKE FAMILIE FW AfD LKR PARTEI Z.SH (+ D14 = independents)
    idx = {"CDU/CSU": 1, "SPD": 2, "Grüne": 3, "FDP": 4, "SSW": 6, "Linke": 7, "Freie Wähler": 9, "AfD": 10}
    agg = {}
    for r in rows:
        a = agg.setdefault(int(r["Wahlkreis"][2:]), {"_v1": 0, "_v2": 0, **{p: [0, 0] for p in idx}})
        a["_v1"] += num(r["Direktstimmen gueltige (D)"]); a["_v2"] += num(r["Listenstimmen gueltige (F)"])
        for p, i in idx.items(): a[p][0] += num(r[f"D{i}"]); a[p][1] += num(r[f"F{i}"])
    D = json.load(open(os.path.join(HERE, "data", "state_wk", "SH.json"), encoding="utf-8"))
    ns = [w["n"] for w in D["wk"]]; miss = [n for n in ns if n not in agg]
    if miss: sys.exit(f"missing constituencies: {miss}")
    res = [{**agg[n], **{p: tuple(agg[n][p]) for p in idx}} for n in ns]
    return share_fill(res, list(idx))

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("NW", "SH"): sys.exit(__doc__)
    sid, src = sys.argv[1], sys.argv[2]
    out = nw(src) if sid == "NW" else sh(src)
    path = write(sid, out)
    lab, srcname = ("2017", "IT.NRW, final result 2017 (first votes), mapped onto the current constituencies by name") if sid == "NW" else \
                   ("2017", "Statistikamt Nord, final result 2017 (first votes; missing candidates filled from second votes)")
    subprocess.check_call([sys.executable, os.path.join(HERE, "py", "add_prev_election.py"), sid, path, "--label", lab, "--source", srcname])

if __name__ == "__main__":
    main()
