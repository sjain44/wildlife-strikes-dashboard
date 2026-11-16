"""Chart builders for the wildlife strike dashboard.

Every function takes an already-filtered DataFrame and returns a plotly Figure,
so the same code draws the charts in the notebook and in the Dash app.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------- style
FONT = "Inter, Segoe UI, Helvetica, Arial, sans-serif"
INK = "#1f2933"
MUTED = "#9aa5b1"
GRID = "#e4e7eb"
ACCENT = "#d9480f"      # the selected species, everywhere
BASE = "#52606d"        # "all strikes", everywhere
DAMAGE_COLORS = {"None": "#cbd2d9", "Minor": "#f7b955", "Substantial": "#e8590c", "Destroyed": "#862e1c"}
SIZE_COLORS = {"Small": "#a5d8ff", "Medium": "#4dabf7", "Large": "#1864ab"}
PHASE_COLOR = "#868e96"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ALL = "All species"


def _layout(fig, title, height=360, **kw):
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=15, color=INK)),
        font=dict(family=FONT, size=12, color=INK),
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=10, r=10, t=56, b=10), height=height,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, size=12, color=INK), align="left"),
        **kw,
    )
    return fig


def label(species):
    return "all strikes" if species in (None, ALL) else species.lower()


# ---------------------------------------------------------------- filtering
def filter_strikes(df, species=None, years=None, airport=None):
    """Apply the dashboard's three controls. None means 'no filter'."""
    mask = pd.Series(True, index=df.index)
    if species not in (None, ALL):
        mask &= df["species"].eq(species)
    if years is not None:
        mask &= df["year"].between(years[0], years[1])
    if airport:
        mask &= df["airport_id"].eq(airport)
    return df[mask]


def kpis(sub):
    n = len(sub)
    known_damage = sub["damage"].ne("Not reported").sum()
    air = sub.loc[sub["airborne"], "height_ft"]
    return {
        "strikes": f"{n:,}",
        "damaging": f"{sub['damaging'].sum() / known_damage:.1%}" if known_damage else "n/a",
        "height": f"{air.median():,.0f} ft" if len(air) else "n/a",
        "night": f"{sub['time_of_day'].eq('Night').sum() / max(sub['time_of_day'].ne('Not reported').sum(), 1):.0%}",
    }


# ---------------------------------------------------------------- 1. line chart
def trend_chart(sub, years=None, species=None):
    """Reports per year next to damaging reports per year (line chart)."""
    yearly = sub.groupby("year").agg(reports=("id", "size"), damaging=("damaging", "sum"),
                                     partial=("partial_year", "any")).reset_index()
    full, part = yearly[~yearly["partial"]], yearly[yearly["partial"]]
    fig = go.Figure()
    for col, name, color in [("reports", "All reports", BASE), ("damaging", "Reports with damage", ACCENT)]:
        fig.add_scatter(x=full["year"], y=full[col], name=name, mode="lines", line=dict(color=color, width=2.5),
                        hovertemplate="%{x}<br>%{y:,} " + name.lower() + "<extra></extra>")
        # the latest year is incomplete, so show it as a hollow point instead of a falling line
        fig.add_scatter(x=part["year"], y=part[col], mode="markers", showlegend=False,
                        marker=dict(symbol="circle-open", size=8, color=color, line=dict(width=2)),
                        hovertemplate="%{x} (partial year)<br>%{y:,} " + name.lower() + "<extra></extra>")
    if years is not None:
        fig.add_vrect(x0=years[0] - 0.5, x1=years[1] + 0.5, fillcolor="#fff4e6", opacity=0.6,
                      layer="below", line_width=0)
    if len(part):
        fig.add_annotation(x=part["year"].iloc[0], y=part["reports"].iloc[0], text="partial year",
                           showarrow=False, yshift=-14, xanchor="right", font=dict(size=10, color=MUTED))
    _layout(fig, f"Reports per year vs reports with damage ({label(species)})",
            legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, rangemode="tozero", title_text="Reports per year")
    return fig


# ---------------------------------------------------------------- 2. radial (polar) chart
def seasonal_radial(context, species=None):
    """Share of strikes in each month, selected species against all strikes (polar bar)."""
    def shares(d):
        s = d["month"].value_counts(normalize=True).reindex(range(1, 13), fill_value=0)
        return (s * 100).round(1)

    fig = go.Figure()
    fig.add_barpolar(r=shares(context), theta=MONTHS, name="All strikes",
                     marker=dict(color=BASE, opacity=0.35, line=dict(width=0)),
                     hovertemplate="%{theta}: %{r}% of all strikes<extra></extra>")
    if species not in (None, ALL):
        sel = context[context["species"].eq(species)]
        if len(sel):
            fig.add_barpolar(r=shares(sel), theta=MONTHS, name=species, width=0.5,
                             marker=dict(color=ACCENT, line=dict(width=0)),
                             hovertemplate="%{theta}: %{r}% of " + species + " strikes<extra></extra>")
    title = ("When in the year (share of strikes by month)" if species in (None, ALL)
             else f"When in the year ({label(species)} vs all strikes)")
    _layout(fig, title,
            legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"))
    fig.update_polars(
        bgcolor="white", hole=0.08,
        angularaxis=dict(direction="clockwise", rotation=90, gridcolor=GRID, linecolor=GRID),
        radialaxis=dict(ticksuffix="%", gridcolor=GRID, linecolor=GRID, tickfont=dict(size=9, color=MUTED), angle=90),
    )
    return fig


# ---------------------------------------------------------------- 3. ridgeline
TICKS = [1, 10, 100, 1000, 10000]


def height_ridgeline(context, species=None, n=10, min_reports=40):
    """Distribution of strike height for the most-reported species (ridgeline).

    Height is on a log scale because it spans 1 ft to 30,000 ft. Each ridge is a
    one-sided violin (a KDE) so the shapes stack without overlapping.
    """
    air = context[context["airborne"] & ~context["unknown_species"].astype(bool)]
    counts = air["species"].value_counts()
    counts = counts[counts >= min_reports]
    chosen = list(counts.index[:n])
    if species not in (None, ALL) and species not in chosen and counts.get(species, 0) >= 5:
        chosen.append(species)
    air = air[air["species"].isin(chosen)]
    order = air.groupby("species", observed=True)["height_ft"].median().sort_values().index.tolist()

    fig = go.Figure()
    medians = []
    for sp in order:
        h = air.loc[air["species"].eq(sp), "height_ft"]
        hit = sp == species
        fig.add_violin(
            x=np.log10(h), y=[sp] * len(h), name=sp, orientation="h", side="positive",
            width=1.9, points=False, spanmode="hard", meanline_visible=False,
            line=dict(color=ACCENT if hit else BASE, width=1.6 if hit else 1),
            fillcolor=ACCENT if hit else "rgba(82,96,109,0.18)", opacity=0.9 if hit else 1,
            hoverinfo="skip",  # the ridge's own hover box floats far outside the plot
        )
        medians.append((sp, h.median(), len(h), hit))
    # one dot per ridge at the median carries a short hover label that stays inside the chart
    m = pd.DataFrame(medians, columns=["species", "median", "n", "hit"])
    fig.add_scatter(
        x=np.log10(m["median"]), y=m["species"], mode="markers",
        marker=dict(size=8, color=np.where(m["hit"], INK, "white"), line=dict(color=INK, width=1.5)),
        customdata=m[["median", "n"]],
        hovertemplate="<b>%{y}</b><br>median %{customdata[0]:,.0f} ft<br>%{customdata[1]:,} airborne strikes<extra></extra>",
    )
    _layout(fig, "How high each species gets hit (airborne strikes, log scale, dot = median)", height=420,
            showlegend=False, hovermode="closest")
    fig.update_xaxes(tickvals=np.log10(TICKS), ticktext=["1 ft", "10", "100", "1,000", "10,000 ft"],
                     gridcolor=GRID, zeroline=False, range=[0, 4.5])
    # leave room above the top ridge so its curve is not clipped
    fig.update_yaxes(categoryorder="array", categoryarray=order, showgrid=False, tickfont=dict(size=11),
                     range=[-0.5, len(order) + 0.4])
    return fig


# ---------------------------------------------------------------- 4. Sankey
def damage_sankey(sub, species=None):
    """Animal size -> phase of flight -> damage (Sankey). Unreported values are left out."""
    d = sub[sub["size"].isin(SIZE_COLORS) & sub["phase_group"].ne("Not reported")
            & sub["damage"].ne("Not reported")]
    sizes = [s for s in SIZE_COLORS if s in set(d["size"])]
    phases = [p for p in ["On the ground", "Take-off and climb", "En route", "Approach and landing"]
              if p in set(d["phase_group"])]
    damages = [x for x in DAMAGE_COLORS if x in set(d["damage"])]
    nodes = sizes + phases + damages
    idx = {name: i for i, name in enumerate(nodes)}

    a = d.groupby(["size", "phase_group"], observed=True).size().reset_index(name="n")
    b = d.groupby(["phase_group", "damage"], observed=True).size().reset_index(name="n")
    # links into the damage column are coloured by damage, links out of size by size
    src = [idx[s] for s in a["size"]] + [idx[p] for p in b["phase_group"]]
    tgt = [idx[p] for p in a["phase_group"]] + [idx[x] for x in b["damage"]]
    val = list(a["n"]) + list(b["n"])
    link_col = [_rgba(SIZE_COLORS[s], 0.35) for s in a["size"]] + [_rgba(DAMAGE_COLORS[x], 0.55) for x in b["damage"]]
    node_col = [SIZE_COLORS[s] for s in sizes] + [PHASE_COLOR] * len(phases) + [DAMAGE_COLORS[x] for x in damages]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=[f"{n} animal" if n in SIZE_COLORS else n for n in nodes], color=node_col,
                  pad=14, thickness=14, line=dict(width=0),
                  hovertemplate="%{label}<br>%{value:,} strikes<extra></extra>"),
        link=dict(source=src, target=tgt, value=val, color=link_col,
                  hovertemplate="%{source.label} → %{target.label}<br>%{value:,} strikes<extra></extra>"),
    ))
    _layout(fig, f"Animal size → phase of flight → damage ({len(d):,} complete reports, {label(species)})",
            height=420)
    return fig


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


# ---------------------------------------------------------------- 5. point map
def airport_map(sub, airport=None, species=None, min_reports=5, bounds=None, place=None):
    """Airports sized by number of strikes, coloured by share that caused damage (point map).

    `bounds` is (lat_min, lat_max, lon_min, lon_max). When given, the map zooms to that box
    and also shows small airports, so a single county's airports are easy to pick.
    """
    if bounds is not None:
        min_reports = 1
    d = sub.dropna(subset=["lat", "lon"])
    known = d["damage"].ne("Not reported")
    g = (d.assign(known=known)
           .groupby(["airport_id", "airport", "state"], observed=True)
           .agg(n=("id", "size"), dmg=("damaging", "sum"), known=("known", "sum"),
                lat=("lat", "first"), lon=("lon", "first"))
           .reset_index())
    g = g[g["n"] >= min_reports].copy()
    g["rate"] = np.where(g["known"] > 0, g["dmg"] / g["known"].clip(lower=1) * 100, 0)
    g = g.sort_values("n")
    sel = g["airport_id"].eq(airport)
    fig = go.Figure()
    fig.add_scattergeo(
        lat=g["lat"], lon=g["lon"], customdata=g[["airport_id", "airport", "state", "n", "rate"]],
        mode="markers",
        marker=dict(size=np.sqrt(g["n"]) * 22 / np.sqrt(max(g["n"].max(), 1)) + 3,
                    color=g["rate"], colorscale=[[0, "#cbd2d9"], [0.3, "#f7b955"], [1, "#862e1c"]],
                    cmin=0, cmax=30, line=dict(width=np.where(sel, 2.5, 0.4), color=np.where(sel, ACCENT, "white")),
                    colorbar=dict(title=dict(text="% damaging", side="right"), thickness=10, len=0.6, ticksuffix="%")),
        hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}, %{customdata[2]}<br>"
                      "%{customdata[3]:,} strikes, %{customdata[4]:.1f}% damaging<extra>click to filter</extra>",
    )
    where = f"zoomed to {place}" if place else f"airports with {min_reports}+ reports"
    _layout(fig, f"Where ({label(species)}, {where}). Click one to filter", height=420)
    fig.update_geos(showland=True, landcolor="#f5f7fa", subunitcolor="#d9dee3", showlakes=False,
                    bgcolor="white", showsubunits=True)
    if bounds is None:
        fig.update_geos(scope="usa")  # Albers USA, with Alaska and Hawaii as insets
    else:
        # the Albers USA projection ignores axis ranges, so a zoomed view switches to Mercator
        lat0, lat1, lon0, lon1 = bounds
        fig.update_geos(scope="north america", projection_type="mercator", resolution=50,
                        showcountries=True, countrycolor="#9aa5b1", subunitcolor="#9aa5b1", subunitwidth=0.8,
                        showlakes=True, lakecolor="#e3eef8", showcoastlines=True, coastlinecolor="#9aa5b1",
                        showocean=True, oceancolor="#e3eef8",
                        lataxis_range=[lat0, lat1], lonaxis_range=[lon0, lon1])
    return fig


# ---------------------------------------------------------------- 6. bar chart
def species_damage_bar(context, species=None, n=12):
    """Share of identified strikes vs share of damaging strikes, by species (grouped bar)."""
    k = context[~context["unknown_species"].astype(bool)]
    g = k.groupby("species", observed=True).agg(n=("id", "size"), dmg=("damaging", "sum"))
    g["strike_share"] = g["n"] / g["n"].sum() * 100
    g["damage_share"] = g["dmg"] / max(g["dmg"].sum(), 1) * 100
    g = g.sort_values("dmg", ascending=False).head(n).iloc[::-1]
    names = g.index.astype(str)
    fig = go.Figure()
    fig.add_bar(y=names, x=g["strike_share"], orientation="h", name="Share of strikes",
                marker_color=[MUTED if s != species else "#f4a582" for s in names],
                hovertemplate="%{y}: %{x:.1f}% of identified strikes<extra></extra>")
    fig.add_bar(y=names, x=g["damage_share"], orientation="h", name="Share of damaging strikes",
                marker_color=[BASE if s != species else ACCENT for s in names],
                hovertemplate="%{y}: %{x:.1f}% of damaging strikes<extra></extra>")
    _layout(fig, "Who does the damage. Click a species to select it", height=420, barmode="group",
            bargap=0.25, legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
    fig.update_xaxes(ticksuffix="%", gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    return fig
