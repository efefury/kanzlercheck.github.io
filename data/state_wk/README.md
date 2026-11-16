# State constituency maps

Drop two files per state into this folder and the state page (`/state/<ID>`) shows a constituency map by itself
(leader / certainty view, zoom, click for details, and it follows the selected poll). No code change, no config change.
States without files simply show no map.

    data/state_wk/<ID>.json      the constituency results of the last state election
    data/state_wk/<ID>.geojson   the constituency boundaries

`<ID>` is the state code: BW BY BE BB HB HH HE MV NI NW RP SL SN ST SH TH

## <ID>.json

    {
      "source": "Landeswahlleiter Baden-Württemberg (final result 2026)",
      "label": "2026",
      "sigma": 6,
      "parties": ["CDU/CSU", "Grüne", "SPD", "AfD", "FDP", "Linke", "Sonstige"],
      "wk": [
        { "n": 1, "name": "Stuttgart I", "v": 61234, "s": [28.1, 30.4, 11.2, 12.0, 6.1, 5.0, 7.2] }
      ]
    }

- `parties`: use the same names as the column headers of the state's poll CSV in `state_polls/` (CDU/CSU, SPD, AfD, Grüne, Linke, FDP, BSW, Freie Wähler ...).
  Put the remainder in a party called `Sonstige` (it never wins a seat; poll parties that are not listed are added to it).
- `wk[].n`: constituency number, must match `properties.n` in the GeoJSON.
- `wk[].s`: result of that constituency in %, one number per party, in the order of `parties`. Use the vote that decides the seat
  (first vote / constituency vote where there are two).
- `wk[].v` (optional): number of voters, used to weight the constituencies when the state total is fitted to the poll. Without it all count equally.
- `sigma` (optional): uncertainty of the lead in points for the "Certainty" view. Default: `stateMapSigma` in `config.json` (6).
- `label` / `source` (optional): shown under the map.

## <ID>.geojson

A GeoJSON FeatureCollection in WGS84 (longitude / latitude), `Polygon` or `MultiPolygon`, one feature per constituency,
with `properties.n` = the constituency number (and, optionally, `name`). Keep it generalised (a few hundred KB at most).
Shapefiles from the state offices can be converted with mapshaper.org or `ogr2ogr -f GeoJSON -t_srs EPSG:4326 out.geojson in.shp`.

## Shortcut: build both files from a CSV

    python py/build_state_wk.py BW results.csv boundaries.geojson [--n-field WKR_NR] [--name-field WKR_NAME]

`results.csv` needs the columns `n`, `name`, optional `voters`, then one column per party with the percentage
(German decimal commas are fine). Writes `data/state_wk/BW.json` and `BW.geojson`.


## Fresher base: `wk[].a` (optional) and `config.json` -> `stateAnchor`

The last state election can be 4-5 years old.  `python py/build_state_anchor.py NW SH NI` adds `wk[].a` to a state's file: the same constituency with the party
geography of the 2025 federal election (first votes, like `s`; mapped onto the Landtag constituencies by overlaying the two boundary files).  `config.json` ->
`stateAnchor: {"NW": 0.8}` is the weight of the projection that starts from `a`; the rest comes from the state-election result `s`.  0 or no entry = old behaviour.
Backtest on the federal elections: a 4-year-old base misses by 1.15 points per party and constituency, an 8-year-old one by 1.76.

## Overhang and compensation seats: `config.json` -> `stateOverhang`

    "stateOverhang": {"NW": {"rule": "full", "odd": true}, "SH": {"rule": "full", "odd": true}, "NI": {"rule": "double"}}

`full`: the house grows until every party's Sainte-Laguë share covers the constituencies it wins (`odd`: only odd sizes, as in NRW and SH).
`double`: the regular size grows by twice the overhang and everything is recalculated (Niedersachsen).  The constituency winners come from the projection on
the state page, so a state needs its `<ID>.json` + `.geojson` here.  Check a state's statute before adding it (Berlin, Brandenburg and Hessen use Hare/Niemeyer,
Bayern compensates per Regierungsbezirk).


## The election before the last one: `wk[].p` (optional)

`python py/add_prev_election.py NW nrw2017.csv --label 2017 --source "..."` adds the previous state election (first votes, on the CURRENT constituency map,
same columns as the main file) to `<ID>.json` as `wk[].p`.  Then blend the bases in `config.json`:

    "stateBlend": {"NW": {"s": 0.2, "p": 0.2, "a": 0.6}}

`s` = last state election, `p` = the one before it, `a` = the 2025 federal result (see above).  The weights are normalised, a base without data is skipped, and
every base is projected to the poll on its own before the projections are averaged.  `stateBlend` replaces `stateAnchor` for that state; without either, only `s` is used.
