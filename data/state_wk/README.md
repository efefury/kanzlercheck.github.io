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
