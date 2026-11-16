"""Wildlife strikes on US aircraft, a linked Plotly + Dash dashboard.

Run locally with `python app.py`, then open http://127.0.0.1:8050.
In production gunicorn serves `app:server`.
"""
from pathlib import Path

import pandas as pd
from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update

import charts as C

HERE = Path(__file__).resolve().parent
DF = pd.read_parquet(HERE / "data" / "strikes_clean.parquet")
YEAR_MIN, YEAR_MAX = int(DF["year"].min()), int(DF["year"].max())

# Dropdown lists identified species with at least 50 reports, most reported first.
_counts = DF.loc[~DF["unknown_species"].astype(bool), "species"].value_counts()
_counts = _counts[_counts >= 50]
SPECIES_OPTIONS = [{"label": "All species", "value": C.ALL}] + [
    {"label": f"{sp} ({n:,})", "value": sp} for sp, n in _counts.items()
]
SPECIES_SET = set(_counts.index)

# Airports with coordinates, for the "Find an airport" search and the state zoom.
AIRPORTS = (DF.dropna(subset=["lat", "lon"]).query("airport_id != 'ZZZZ'")
              .groupby(["airport_id", "airport", "state"], observed=True)
              .agg(n=("id", "size"), lat=("lat", "first"), lon=("lon", "first"))
              .reset_index().sort_values("n", ascending=False))
AIRPORT_OPTIONS = [{"label": f"{r.airport_id}  {str(r.airport).title()}, {r.state} ({r.n:,})",
                    "value": r.airport_id} for r in AIRPORTS.itertuples()]
AIRPORT_STATE = dict(zip(AIRPORTS["airport_id"], AIRPORTS["state"].astype(str)))

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin",
    "WY": "Wyoming", "PR": "Puerto Rico",
}


def _bounds(g):
    """A lat/lon box around a group of airports, padded so edge airports are not cut off."""
    lat0, lat1, lon0, lon1 = g["lat"].min(), g["lat"].max(), g["lon"].min(), g["lon"].max()
    pad_lat, pad_lon = max(0.5, (lat1 - lat0) * 0.08), max(0.7, (lon1 - lon0) * 0.08)
    return (float(lat0 - pad_lat), float(lat1 + pad_lat), float(lon0 - pad_lon), float(lon1 + pad_lon))


STATE_BOUNDS = {st: _bounds(g) for st, g in AIRPORTS.groupby(AIRPORTS["state"].astype(str))
                if st in STATE_NAMES}
STATE_OPTIONS = [{"label": STATE_NAMES[st], "value": st} for st in sorted(STATE_BOUNDS, key=STATE_NAMES.get)]

app = Dash(__name__, title="Wildlife Strikes Dashboard")
server = app.server  # for gunicorn


GRAPH_CONFIG = {
    "displayModeBar": "hover",   # shows a small toolbar with the reset-view button on hover
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage", "autoScale2d"],
}
RESET_LABELS = {"species": "Clear species", "years": "Show all years", "airport": "Clear airport"}


MAP_CONFIG = {**GRAPH_CONFIG, "displayModeBar": True, "scrollZoom": True}  # always show +/- and reset


def card(graph_id, note, resets, tools=None, config=GRAPH_CONFIG):
    """A chart, a one-line note, and a reset button for the filter this chart controls."""
    return html.Div(className="card", children=[
        *([html.Div(className="map-tools", children=tools)] if tools else []),
        dcc.Graph(id=graph_id, config=config),
        html.Div(className="card-footer", children=[
            html.P(note, className="note"),
            html.Button(RESET_LABELS[resets], className="card-reset", n_clicks=0,
                        id={"type": "card-reset", "chart": graph_id, "target": resets}),
        ]),
    ])


def kpi(kpi_id, caption):
    return html.Div(className="kpi", children=[html.Div(id=kpi_id, className="kpi-value"),
                                               html.Div(caption, className="kpi-caption")])


app.layout = html.Div(className="page", children=[
    html.Header(children=[
        html.H1("Which animals actually damage aircraft, and when?"),
        html.P("Pilots report about 20,000 wildlife strikes a year, but only a few of them damage the plane. "
               "This dashboard helps you answer four questions."),
        html.Ol(className="questions", children=[
            html.Li([html.B("Is it getting more dangerous, or are people just reporting more? "),
                     "Drag the year range and compare the two lines."]),
            html.Li([html.B("Which animals are rare but cause most of the damage? "),
                     "Look for a long dark bar next to a short grey one."]),
            html.Li([html.B("When in the year, and how high up, does each animal get hit? "),
                     "Pick a species and watch the polar chart and the ridgeline."]),
            html.Li([html.B("Where, and in which part of the flight, does the damage happen? "),
                     "Follow the Sankey, then click an airport on the map."]),
        ]),
        html.P(className="how", children=[
            "Pick a species, drag the years, click a bar, a median dot or an airport, or zoom the map to a state. Every chart updates "
            "together, and each chart has its own reset button. Data from the ",
            html.A("FAA National Wildlife Strike Database", href="https://wildlife.faa.gov/search",
                   target="_blank"), ", 1990 to 2026."]),
    ]),
    html.Div(className="controls", children=[
        html.Div(className="control species", children=[
            html.Label("Species", htmlFor="species"),
            dcc.Dropdown(id="species", options=SPECIES_OPTIONS, value=C.ALL, clearable=False),
        ]),
        html.Div(className="control years", children=[
            html.Label("Years"),
            dcc.RangeSlider(id="years", min=YEAR_MIN, max=YEAR_MAX, step=1, value=[YEAR_MIN, YEAR_MAX],
                            marks={y: str(y) for y in range(1990, YEAR_MAX + 1, 10)},
                            tooltip={"placement": "bottom", "always_visible": False}),
        ]),
        html.Div(className="control buttons", children=[
            html.Div(id="airport-chip", className="chip"),
            html.Button("Reset all", id="reset", n_clicks=0),
        ]),
    ]),
    dcc.Store(id="airport"),
    html.Div(className="kpis", children=[
        kpi("k-strikes", "reported strikes"),
        kpi("k-damaging", "caused damage (of reports that say)"),
        kpi("k-height", "median height when airborne"),
        kpi("k-night", "at night (of reports that say)"),
    ]),
    html.Div(className="grid", children=[
        card("trend", "Line chart. The shaded band is the selected year range.", "years"),
        card("radial", "Polar bar chart. Each wedge is the share of the year's strikes in that month.", "species"),
        card("bar", "Grouped bars. Click a species to select it.", "species"),
        card("ridge", "Ridgeline of strike height. Hover or click a median dot.", "species"),
        card("sankey", "Sankey. Band width is the number of strikes. Hover a band for counts.", "species"),
        card("map", "Point map. Size is strikes, colour is share damaging. Scroll or use + and - to zoom, "
                    "click an airport to filter.", "airport", config=MAP_CONFIG, tools=[
            dcc.Dropdown(id="map-state", options=STATE_OPTIONS, placeholder="Zoom to a state",
                         clearable=True, className="map-state"),
            dcc.Dropdown(id="airport-pick", options=AIRPORT_OPTIONS,
                         placeholder="Find an airport (e.g. KDTW, Detroit)", clearable=True,
                         className="airport-pick"),
        ]),
    ]),
    html.Footer("Built with Plotly and Dash. Reporting is voluntary, so counts are reports, not all strikes. "
                "2026 is a partial year."),
])


@app.callback(
    Output("species", "value"), Output("years", "value"), Output("airport", "data"),
    Output("airport-pick", "value"), Output("map-state", "value"),
    Input("bar", "clickData"), Input("ridge", "clickData"), Input("map", "clickData"),
    Input("airport-pick", "value"),
    Input("reset", "n_clicks"), Input({"type": "card-reset", "chart": ALL, "target": ALL}, "n_clicks"),
    State("species", "value"), State("airport", "data"),
    prevent_initial_call=True,
)
def handle_clicks(bar_click, ridge_click, map_click, picked, _reset, _card_resets, species, airport):
    """Clicks on one chart become filters for all the others. Reset buttons clear them."""
    trigger = ctx.triggered_id
    skip = (no_update,) * 5
    if trigger == "reset":
        return C.ALL, [YEAR_MIN, YEAR_MAX], None, None, None
    if isinstance(trigger, dict) and trigger.get("type") == "card-reset":
        if not ctx.triggered[0]["value"]:      # ignore the buttons being created
            return skip
        target = trigger["target"]
        if target == "airport":                # also zoom the map back out
            return no_update, no_update, None, None, None
        return (C.ALL if target == "species" else no_update,
                [YEAR_MIN, YEAR_MAX] if target == "years" else no_update, no_update, no_update, no_update)
    if trigger == "bar" and bar_click:
        sp = bar_click["points"][0]["y"]
        return (C.ALL if sp == species else sp), no_update, no_update, no_update, no_update
    if trigger == "ridge" and ridge_click:
        sp = ridge_click["points"][0].get("y")
        if sp in SPECIES_SET:
            return (C.ALL if sp == species else sp), no_update, no_update, no_update, no_update
    if trigger == "map" and map_click:
        code = map_click["points"][0]["customdata"][0]
        code = None if code == airport else code
        return no_update, no_update, code, code, no_update
    if trigger == "airport-pick":
        return no_update, no_update, picked, no_update, no_update
    return skip


@app.callback(
    Output("trend", "figure"), Output("radial", "figure"), Output("bar", "figure"),
    Output("ridge", "figure"), Output("sankey", "figure"), Output("map", "figure"),
    Output("k-strikes", "children"), Output("k-damaging", "children"),
    Output("k-height", "children"), Output("k-night", "children"), Output("airport-chip", "children"),
    Input("species", "value"), Input("years", "value"), Input("airport", "data"),
    Input("map-state", "value"),
)
def update(species, years, airport, map_state=None):
    """One control change redraws all six charts and the four headline numbers."""
    selected = C.filter_strikes(DF, species, years, airport)          # all three filters
    context = C.filter_strikes(DF, None, years, airport)              # every species, for comparison
    over_time = C.filter_strikes(DF, species, None, airport)          # every year, for the trend line
    on_map = C.filter_strikes(DF, species, years, None)               # every airport, so the map stays clickable
    k = C.kpis(selected)
    chip = "" if not airport else f"Airport {airport} (click it again to clear)"
    # zoom to the chosen state, or else to the state of the chosen airport
    zoom_state = map_state or AIRPORT_STATE.get(airport)
    bounds = STATE_BOUNDS.get(zoom_state)
    place = STATE_NAMES.get(zoom_state) if bounds else None
    return (
        C.trend_chart(over_time, years, species),
        C.seasonal_radial(context, species),
        C.species_damage_bar(context, species),
        C.height_ridgeline(context, species),
        C.damage_sankey(selected, species),
        C.airport_map(on_map, airport, species, bounds=bounds, place=place),
        k["strikes"], k["damaging"], k["height"], k["night"], chip,
    )


if __name__ == "__main__":
    app.run(debug=False, port=8050)
