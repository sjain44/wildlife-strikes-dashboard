"""Wildlife strikes on US aircraft, a linked Plotly + Dash dashboard.

Run locally with `python app.py`, then open http://127.0.0.1:8050.
In production gunicorn serves `app:server`.
"""
from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

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

app = Dash(__name__, title="Wildlife Strikes Dashboard")
server = app.server  # for gunicorn


def card(graph_id, note):
    return html.Div(className="card", children=[
        dcc.Graph(id=graph_id, config={"displayModeBar": False}),
        html.P(note, className="note"),
    ])


def kpi(kpi_id, caption):
    return html.Div(className="kpi", children=[html.Div(id=kpi_id, className="kpi-value"),
                                               html.Div(caption, className="kpi-caption")])


app.layout = html.Div(className="page", children=[
    html.Header(children=[
        html.H1("Which animals actually damage aircraft, and when?"),
        html.P(["360,000 wildlife strikes reported to the FAA, 1990 to 2026. Pick a species, drag the "
                "year range, or click a bar, ridge or airport. Every chart updates together. ",
                html.A("Data: FAA National Wildlife Strike Database",
                       href="https://wildlife.faa.gov/search", target="_blank")]),
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
        card("trend", "Line chart. The shaded band is the selected year range."),
        card("radial", "Polar bar chart. Each wedge is the share of the year's strikes in that month."),
        card("bar", "Grouped bars. A long dark bar next to a short grey one means a rare but damaging animal."),
        card("ridge", "Ridgeline. Each ridge is a smoothed distribution of strike height, ordered by median."),
        card("sankey", "Sankey. Band width is the number of strikes. Hover a band for counts."),
        card("map", "Point map. Circle size is strikes, colour is the share that caused damage."),
    ]),
    html.Footer("Built with Plotly and Dash. Reporting is voluntary, so counts are reports, not all strikes. "
                "2026 is a partial year."),
])


@app.callback(
    Output("species", "value"), Output("years", "value"), Output("airport", "data"),
    Input("bar", "clickData"), Input("ridge", "clickData"), Input("map", "clickData"),
    Input("reset", "n_clicks"),
    State("species", "value"), State("airport", "data"),
    prevent_initial_call=True,
)
def handle_clicks(bar_click, ridge_click, map_click, _reset, species, airport):
    """Clicks on one chart become filters for all the others."""
    trigger = ctx.triggered_id
    if trigger == "reset":
        return C.ALL, [YEAR_MIN, YEAR_MAX], None
    if trigger == "bar" and bar_click:
        sp = bar_click["points"][0]["y"]
        return (C.ALL if sp == species else sp), no_update, no_update
    if trigger == "ridge" and ridge_click:
        sp = ridge_click["points"][0].get("y")
        if sp in SPECIES_SET:
            return (C.ALL if sp == species else sp), no_update, no_update
    if trigger == "map" and map_click:
        code = map_click["points"][0]["customdata"][0]
        return no_update, no_update, (None if code == airport else code)
    return no_update, no_update, no_update


@app.callback(
    Output("trend", "figure"), Output("radial", "figure"), Output("bar", "figure"),
    Output("ridge", "figure"), Output("sankey", "figure"), Output("map", "figure"),
    Output("k-strikes", "children"), Output("k-damaging", "children"),
    Output("k-height", "children"), Output("k-night", "children"), Output("airport-chip", "children"),
    Input("species", "value"), Input("years", "value"), Input("airport", "data"),
)
def update(species, years, airport):
    """One control change redraws all six charts and the four headline numbers."""
    selected = C.filter_strikes(DF, species, years, airport)          # all three filters
    context = C.filter_strikes(DF, None, years, airport)              # every species, for comparison
    over_time = C.filter_strikes(DF, species, None, airport)          # every year, for the trend line
    on_map = C.filter_strikes(DF, species, years, None)               # every airport, so the map stays clickable
    k = C.kpis(selected)
    chip = "" if not airport else f"Airport {airport} (click it again to clear)"
    return (
        C.trend_chart(over_time, years, species),
        C.seasonal_radial(context, species),
        C.species_damage_bar(context, species),
        C.height_ridgeline(context, species),
        C.damage_sankey(selected, species),
        C.airport_map(on_map, airport, species),
        k["strikes"], k["damaging"], k["height"], k["night"], chip,
    )


if __name__ == "__main__":
    app.run(debug=False, port=8050)
