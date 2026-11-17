"""Assemble wildlife_strikes_dashboard.ipynb from prose, prepare_data.py steps and screenshots.

The cleaning cells are cut straight out of prepare_data.py, so the notebook and the
script cannot drift apart. Run, then execute the notebook with nbclient.
"""
import base64
import re
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"
OUT = ROOT / "wildlife_strikes_dashboard.ipynb"

LIVE_URL = "https://wildlife-strikes-2zcv.onrender.com"
REPO_URL = "https://github.com/sjain44/wildlife-strikes-dashboard"
VIDEO_URL = "https://github.com/sjain44/wildlife-strikes-dashboard/blob/main/video/wildlife_strikes_walkthrough.mp4"

steps = {}
for block in re.split(r"^# %% step: ", (ROOT / "prepare_data.py").read_text(encoding="utf-8"), flags=re.M)[1:]:
    name, code = block.split("\n", 1)
    steps[name.strip()] = code.strip()

cells = []


def md(text, images=()):
    cell = nbf.v4.new_markdown_cell(text.strip())
    if images:
        cell["attachments"] = {
            name: {"image/png": base64.b64encode((IMG / name).read_bytes()).decode()} for name in images
        }
    cells.append(cell)


def code(text):
    cells.append(nbf.v4.new_code_cell(text.strip()))


def img(name, alt):
    return f"![{alt}](attachment:{name})"


# =====================================================================================
md(f"""
# Which animals actually damage aircraft, and when?
### A linked Plotly + Dash dashboard of 360,000 FAA wildlife strike reports

**Live dashboard** {LIVE_URL} (free host, so the first load can take up to a minute)
**Code** {REPO_URL}
**Video** {VIDEO_URL}
""")

md(f"""
## 1. Introduction

It is fall in Michigan, and lately I keep seeing big V's of Canada geese flying over my place. I live near Detroit Metro Airport (DTW), so planes are coming in and out over the same fields and ponds the geese use. That got me wondering. **How much have Canada geese actually affected planes flying in and out of Detroit Metro over the past 10 years?**

To answer that I needed more than one chart. I needed to see Detroit next to the rest of the country, geese next to every other animal, and fall next to the rest of the year. So I built a dashboard on the FAA's wildlife strike data around four broader questions.

1. **Is flying getting more dangerous, or are people just reporting more strikes?**
2. **Which animals are rare but cause most of the damage?**
3. **When in the year, and how high up, does each animal get hit?**
4. **Where, and in which part of the flight, does the damage happen?**

You pick a species, a range of years or an airport, and six charts update together to answer them. The short answer to my geese question surprised me, and it is in section 5.

{img("03_full_layout.png", "Finished dashboard")}
""", images=["03_full_layout.png"])

# =====================================================================================
md("""
## 2. Library choice and fit

I went with **Plotly** for the charts and **Dash** to tie them together into one app.

| | Plotly (plotly.py, plotly.js) | Dash |
| --- | --- | --- |
| Who made it | Plotly Technologies, started in Montreal in 2012 by Alex Johnson, Jack Parmer, Chris Parmer and Matthew Sundquist | the same company, first released in 2017 with Chris Parmer leading it |
| License | MIT | MIT |
| Install | `pip install plotly` | `pip install dash` (this also installs plotly and Flask) |
| Version I used | plotly 7.1.0 | dash 4.5.0 |

**Declarative, not procedural.** With Plotly I describe what the chart should look like as a big JSON-style object, and plotly.js figures out how to draw it. That felt very different from writing drawing commands line by line. Dash works the same way. I describe the page as a tree of components, and for each callback I just say which inputs it listens to and which outputs it changes. Dash decides when to run it.

**Jupyter.** Plotly charts show up right inside JupyterLab, VS Code and Colab, and you can even run a whole Dash app inside a notebook with `app.run(jupyter_mode="inline")`. In this notebook I save the charts as plain images with `kaleido`, so they still show up when the notebook is turned into HTML or PDF.

**The limitations I ran into**
- Dash needs a Python server running behind it. That means I could not just save the dashboard as one HTML file. It has to be hosted somewhere, and free hosts put the app to sleep when nobody is using it.
- Plotly has no ridgeline chart. I had to fake one by stacking half-violins. Violins do their smoothing in the browser, so this one chart sends about 0.34 MB of raw numbers every time something changes.
- The map draws every point as SVG, which gets very slow with lots of points. Plotting all 300,000 strikes would freeze the page, so I grouped them into 1,186 airports.
- Dash changes quickly. Dash 3 removed `app.run_server`, and Dash 4 replaced the dropdown and the range slider. A lot of the examples I found online simply do not work anymore.

**Why it fits this data.** There are 360,000 rows, which is a lot to push into a browser. With Dash the filtering happens on the server with pandas, which takes about 0.3 seconds, and only six small finished charts get sent to the page. My questions also needed some unusual chart types, like a Sankey for flows, polar bars for a yearly cycle, violins for distributions and a US map that includes Alaska and Hawaii. Plotly has all of these built in. It also reports which bar, ridge or map point you clicked, and that is exactly what I needed to make clicks work as filters.

**What I decided against.** My first idea was Bokeh, since it can save everything as one HTML file and I would not have needed a server. The problem was that all 360,000 rows would have to live inside that file. I would also have had to write the Sankey, the smoothing and the airport totals myself in JavaScript, and Bokeh does not have a Sankey unless you add HoloViews on top. I also thought about Streamlit, but it reruns the whole script every time you touch a control, and its chart selection is built around dragging a box or lasso, not clicking one bar.
""")

# =====================================================================================
md("""
## 3. Data

The data comes from the **FAA National Wildlife Strike Database** (https://wildlife.faa.gov/search). The "Download Excel" button gives you a 133 MB zip file with one big spreadsheet inside. I downloaded it on 16 November 2026. It is US government data, so it is in the public domain, and the FAA already hides the names of the people who filed the reports.

The raw file has 360,384 rows and 102 columns, going from 1990 to October 2026. One thing to keep in mind is that reporting is voluntary. Every number in this project is really a count of *reports*, not of every strike that happened.

Here are the columns I ended up using.

| Column (renamed) | What it holds | How complete |
| --- | --- | --- |
| `date`, `year`, `month` | when it happened | 100% |
| `time_of_day` | Day, Night, Dusk, Dawn | 56% |
| `airport_id`, `airport`, `state`, `lat`, `lon` | where it happened | 86% |
| `phase` | part of the flight, 12 values | 60% |
| `height_ft`, `speed_kt` | feet above ground, knots | 49%, 31% |
| `damage_code` | N none, M minor, M? uncertain, S substantial, D destroyed | 65% |
| `species`, `size` | what got hit, and whether it was small, medium or large | 100%, 88% |
| `num_struck`, `operator`, `ac_class` | extra context | 72 to 100% |

### Cleaning steps
Every cell below is copied straight from `prepare_data.py`, so running that one script gives you exactly the same clean file.
""")
code("""
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
""" + steps["setup"])
md("First I download the zip file, but only if I do not already have it, and unzip it.")
code(steps["download"])
md("Then I read the spreadsheet. The `calamine` engine reads it in about 35 seconds, which is way faster than the default. I also turn every text column into a clean string, because some columns like `AIRPORT_ID` mix numbers and text and the file would not save otherwise.")
code(steps["read"])
md("Eight report IDs showed up twice. When I looked closer, the only difference was the species name, either Squirrels or Tree squirrels. So it is a lookup mistake, and I keep the more specific name.")
code(steps["duplicates"] + "\ndups[['INDEX_NR', 'INCIDENT_DATE', 'AIRPORT_ID', 'SPECIES']].head(4)")
md("Out of 102 columns I only need 20, so I keep those and give them names that are easier to read.")
code(steps["select"] + "\ndf.head(3)")
md("Dates and coordinates come in as text, so I turn them into real dates and numbers. I also flag the latest year, because the FAA had only checked reports up to about August when I downloaded it.")
code(steps["types"])
md("Next I turn the damage codes into words. I count a strike as damaging if any damage at all was reported. If the field is blank I call it Not reported, because a blank does not mean nothing happened.")
code(steps["damage"] + "\ndf['damage'].value_counts()")
md("There are twelve flight phases, which is too many for one chart, so I group them into four.")
code(steps["phase"] + "\ndf['phase_group'].value_counts()")
md("About 40% of reports just say something like Unknown bird. I keep them in the totals but flag them, so they do not show up as a fake species in the species charts.")
code(steps["species"] + "\nround(df['unknown_species'].mean(), 3)")
md("A height of 0 means the animal was hit on the runway, so the height charts only use strikes that happened in the air.")
code(steps["height"] + "\ndf['airborne'].sum()")
md("Last, I store the text columns as categories and save a 7 MB parquet file. That small file is the only data the dashboard needs.")
code(steps["save"])
md("""
I also noticed two quirks while cleaning. The airport code `ZZZZ` means the airport is unknown. That covers 48,847 reports, and since they have no coordinates they just do not appear on the map. The other one surprised me. 86% of the heights are multiples of 50 ft, which means pilots are estimating. So when the height chart shows little bumps at 50, 100 and 500 ft, that is people rounding, not birds.
""")
code("""
air = df.loc[df['airborne'], 'height_ft']
pd.Series({'airborne reports': len(air),
           'multiple of 50 ft': round((air % 50 == 0).mean(), 3),
           'unknown airport (ZZZZ)': int(df['airport_id'].eq('ZZZZ').sum())})
""")

# =====================================================================================
md("""
## 4. Visualization techniques

Each chart lives in `charts.py` as a function. It takes the filtered data and hands back a finished chart, so this notebook and the live app draw exactly the same thing.
""")
code("""
import plotly.io as pio
import charts as C

pio.renderers.default = "png"          # static images so the figures survive HTML/PDF export
pio.renderers["png"].width = 1000
""")

md("""
| Chart | What it shows | Why I used it here | When you should not use it |
| --- | --- | --- | --- |
| **Line chart** (covered in class) | reports per year next to damaging reports per year | the reporting trend is the backdrop for every other number | when the x-axis has no natural order, or with lots of lines crossing each other |
| **Polar bar chart** (new to class) | the share of strikes in each month, for the chosen species and for everything | migration goes in a circle, and December really does sit next to January | for anything that is not a cycle, or when exact comparisons matter, since angles and areas are harder to read than bar lengths |
| **Grouped bar chart** (covered in class) | each species' share of strikes next to its share of the damage | it shows right away which animals are rare but costly | with more than about 15 categories, or when the two measures use different units |
| **Ridgeline** (new to class) | the full spread of strike heights for 10 or 11 species, sorted by median | the heights are skewed and lumpy, so I wanted to compare whole shapes instead of one average | when a group has only a few points (the smoothing makes up a shape), or when you need exact numbers |
| **Sankey diagram** (new to class) | strikes flowing from animal size to flight phase to damage | damage depends on two things in a row, and the band widths keep the counts honest | for flows that loop back, or with so many nodes that it turns into spaghetti |
| **Point map** (covered in class) | airports sized by number of reports and coloured by how often there was damage | it answers where, and clicking an airport filters everything else | when people will read circle size as danger (it mostly shows traffic), or when points pile on top of each other |
""")

md("""
### What the new chart types show that the usual ones miss
**Ridgeline vs box plot.** Below are the same heights drawn as box plots. The box for Canada goose goes from about 60 to 1,500 ft, which tells me the range but not the shape. The ridgeline right after it shows the real picture. Goose strikes are spread out like a wide plateau, while doves and swallows pile up under 100 ft. The box plot also completely hides those rounding bumps I found during cleaning.
""")
code("""
import plotly.express as px
keep = ['Barn swallow', 'Mourning dove', 'Gulls', 'Canada goose', 'Turkey vulture', 'Snowy owl']
air = df[df['airborne'] & df['species'].isin(keep)].copy()
air['species'] = air['species'].astype(str)
box = px.box(air, x='height_ft', y='species', log_x=True, points=False,
             category_orders={'species': keep[::-1]}, title='The usual way. Box plots of strike height')
box.update_traces(marker_color=C.BASE).update_layout(height=330, template='simple_white')
box.show()
""")
code("""
C.height_ridgeline(df, species='Canada goose').show()
""")
md("""
**Polar bars vs a line chart.** At Detroit Metro, snowy owl strikes run from November through March. On a normal January-to-December line, that season gets cut in two, with one piece at the far left and the other at the far right. On the polar chart it stays in one piece, sitting on the opposite side of the circle from DTW's summer peak.
""")
code("""
dtw_ten = df[df['airport_id'].eq('KDTW') & df['year'].between(2016, 2025)]
C.seasonal_radial(dtw_ten, species='Snowy owl').show()
""")
md("""
**Sankey vs a stacked bar.** A stacked bar can show damage by flight phase or damage by animal size, but not both at once. The Sankey follows each strike through both steps. You can see large animals flowing mostly into approach and landing, and that is where most of the orange damage bands start.
""")
code("""
C.damage_sankey(df).show()
""")
md("""
### How the charts fit together
I laid the page out so it reads like a story from top to bottom. The top row covers how much and when, with the trend and the season. The middle row is about who, with the bar chart and the ridgeline side by side, since clicking either one picks a species. The bottom row shows how and where, with the Sankey and the map. Orange always means the species you picked, and grey always means everything, so you can follow one choice across all six charts.
""")

# =====================================================================================
md("""
## 5. Building and exploring

### Step 1. One chart at a time
I started by building each chart as its own function and testing it on the full data before connecting anything. The ridgeline took the most work, so here is its code.
""")
code("""
import inspect
from IPython.display import Markdown
Markdown("```python\\n" + inspect.getsource(C.height_ridgeline) + "\\n```")
""")
md(f"""
{img("02_chart_trend.png", "line")} {img("02_chart_radial.png", "polar")}
{img("02_chart_bar.png", "bars")} {img("02_chart_ridge.png", "ridgeline")}
""", images=["02_chart_trend.png", "02_chart_radial.png", "02_chart_bar.png", "02_chart_ridge.png"])

md("""
### Step 2. Putting the page together
Next came the layout. There is a control bar that sticks to the top while you scroll, then four headline numbers, then the six charts in a two-column grid. The styling is in `assets/style.css`. On a phone the grid switches to one column. My first try squished every chart down to a few pixels tall, which is entry 2 in the AI log.

```python
app.layout = html.Div(className="page", children=[
    html.Header(...),
    html.Div(className="controls", children=[dcc.Dropdown(id="species", ...),
                                             dcc.RangeSlider(id="years", ...),
                                             html.Button("Reset all", id="reset")]),
    dcc.Store(id="airport"),                       # holds the airport picked on the map
    html.Div(className="kpis", children=[...]),
    html.Div(className="grid", children=[card("trend", note, "years"), card("radial", note, "species"),
                                         card("bar", note, "species"), card("ridge", note, "species"),
                                         card("sankey", note, "species"), card("map", note, "airport")]),
])
```
Each `card` holds a chart, a one-line note and a reset button for the filter that chart controls.
""")

md("""
### Step 3. Linking the charts
The linking only takes two callbacks. The first one turns clicks into filter values. The second one takes those values and redraws everything.

| What you do | What updates |
| --- | --- |
| Pick a species in the dropdown | all six charts and all four numbers |
| Click a bar or a ridgeline median dot | picks that species, so everything again |
| Drag the year slider | all six charts (the trend chart shades the years you picked) |
| Click an airport on the map, or type one into Find an airport | filters the other five charts to that airport and zooms the map to its state |
| Zoom to a state (above the map) | zooms the map so single airports are easy to pick |
| A chart's own reset button | clears just that chart's filter (Show all years, Clear species, Clear airport) |
| Hit Reset all | clears everything |

Each chart also shows a small toolbar on hover with a button to reset its zoom. The map keeps its + and - zoom buttons visible all the time and also zooms with the scroll wheel. Once it is zoomed in, it switches from the national map projection to a regular one and shows lakes and state borders, so you can find something like Detroit Metro in Wayne County, Michigan.

Each chart ignores the one filter that would make it useless. The trend chart always shows every year so the shaded band has something to compare to. The map always shows every airport so you can click a different one. The bar chart and ridgeline always show every species, because that is where you pick one.
""")
code("""
import app as A
Markdown("```python\\n" + inspect.getsource(A.handle_clicks) + "\\n" + inspect.getsource(A.update) + "\\n```")
""")
md("""
To make sure the links actually worked, I wrote a Playwright script (`scripts/shoot.py`). It opens the running app in Edge, clicks through every control, prints the four headline numbers after each step and saves the screenshots you see in this notebook. Every control changed the numbers, and reset put them back.

```
initial            ['360,376', '9.6%',  '600 ft',   '31%']
snow goose         ['211',     '77.0%', '2,000 ft', '73%']  Snow goose (211)
after bar click    ['7,728',   '18.6%', '200 ft',   '14%']  Gulls (7,728)
after map click    ['92',      '19.1%', '500 ft',   '20%']  Airport KDEN*
after ridge click  ['1,399',   '56.8%', '800 ft',   '2%']   Turkey vulture (1,399)
years 2015+        ['203,212', '6.8%',  '800 ft',   '32%']
after reset        ['360,376', '9.6%',  '600 ft',   '31%']
phone scroll width 390, console errors []
```
""")

md("""
### What I found

**Where I started.** My real question was about the geese I see over Detroit every fall. How often do they hit planes at DTW, do those hits do damage, and is fall the dangerous time? I also wanted to know whether the rising number of strike reports nationwide means flying is getting more dangerous.

**First, the national trend is mostly more reporting.** When I dragged the year slider from the 1990s to the 2020s, reports went up about six times, from around 3,100 a year to 18,500 a year. Damaging strikes only went up about one and a half times, from 486 to 719 a year, and the share that caused damage dropped from 19.2% to 6.5%. Airports are reporting a lot more of the small stuff, so a rising line does not mean flying got more dangerous. That matters for Detroit too, because a busy, careful airport will report lots of harmless strikes.
""")
code("""
decades = {'1990-99': (1990, 1999), '2000-09': (2000, 2009), '2010-19': (2010, 2019), '2020-25': (2020, 2025)}
rows = {}
for name, (a, b) in decades.items():
    s = df[df['year'].between(a, b)]
    known = s['damage'].ne('Not reported')
    rows[name] = {'reports per year': round(len(s) / (b - a + 1)),
                  'damaging per year': round(s['damaging'].sum() / (b - a + 1)),
                  'damaging share of known': f"{s['damaging'].sum() / known.sum():.1%}",
                  'damage field filled': f"{known.mean():.0%}"}
pd.DataFrame(rows).T
""")
md(f"""
**Zooming in on Detroit Metro.** I set the years to 2016 to 2025 (the last 10 full years), typed KDTW into the new Find an airport box, and the whole dashboard switched to Detroit. DTW reported 2,679 strikes in those 10 years. The polar chart shows they pile up in summer, with 43% in July and August alone. Fall (September to November) is 25%, and the fall strikes are mostly mourning doves, horned larks and killdeer, not geese.

{img("story_1_dtw.png", "Dashboard filtered to Detroit Metro, 2016 to 2025")}
""", images=["story_1_dtw.png"])
md(f"""
**Then I picked Canada goose.** The headline number dropped to **8**. In 10 years, only 8 of DTW's 2,679 strikes were Canada geese, which is 0.3%. None of them happened in September, October or November. Only one caused any damage, a minor one in August 2017 when a plane hit a small group of geese while landing at dusk. I double-checked that geese were not hiding under other labels. DTW has no other goose or "geese" entries, the nearby airports (Willow Run, Pontiac, Detroit City) report no geese at all, and the 8 "Unknown bird, large" strikes could be anything.

{img("story_2_dtw_goose_trend.png", "Canada goose strikes at DTW by year")}
""", images=["story_2_dtw_goose_trend.png"])
md(f"""
**So are geese harmless? Not at all.** When I cleared the airport and kept Canada goose selected for 2016 to 2025, the national picture was completely different. There were 707 Canada goose strikes across the US, and 53% of the ones that reported damage had some. 25 caused substantial damage or destroyed something, and 38% involved more than one goose, because they fly in flocks. Nationally their peak is August and September (24% of goose strikes), right as they start moving around for fall. The Sankey shows those big birds flowing into approach and landing and then into the orange damage bands. Zooming the map to Michigan shows only 22 Canada goose strikes in the whole state over those 10 years, and 8 of them are DTW's.

{img("story_3_us_goose_radial.png", "Canada goose season, US")} {img("story_3_us_goose_sankey.png", "Canada goose Sankey, US")}
{img("story_3_michigan_goose_map.png", "Canada goose strikes in Michigan")}
""", images=["story_3_us_goose_radial.png", "story_3_us_goose_sankey.png", "story_3_michigan_goose_map.png"])
code("""
def profile(sub):
    known = sub['damage'].ne('Not reported'); tod = sub['time_of_day'].ne('Not reported')
    months = sub['month'].value_counts(normalize=True)
    return {'reports': len(sub),
            'damaging (of reports that say)': f"{sub['damaging'].sum()} of {known.sum()}",
            'fall share (Sep-Nov)': f"{months.reindex([9, 10, 11]).fillna(0).sum():.0%}",
            'summer share (Jul-Aug)': f"{months.reindex([7, 8]).fillna(0).sum():.0%}",
            'winter share (Dec-Mar)': f"{months.reindex([12, 1, 2, 3]).fillna(0).sum():.0%}"}

ten = df[df['year'].between(2016, 2025)]
dtw = ten[ten['airport_id'].eq('KDTW')]
pd.DataFrame({'DTW, every animal': profile(dtw),
              'DTW, Canada goose': profile(dtw[dtw['species'].eq('Canada goose')]),
              'US, Canada goose': profile(ten[ten['species'].eq('Canada goose')]),
              'DTW, snowy owl': profile(dtw[dtw['species'].eq('Snowy owl')])})
""")
md(f"""
**What actually damages planes at DTW.** Back on Detroit with all species, the bar chart answers this right away. The top two are **snowy owls** and **red-tailed hawks**, with 4 damaging strikes each, then herring gulls with 3. Snowy owls really stood out. They are under 1% of DTW's strikes but about 15% of its damaging strikes where the species is known, and when I selected them the polar chart flipped to winter. All 22 of DTW's snowy owl strikes happened between November and March, with 9 in March alone. Two of them did substantial damage. That is a pattern I never would have thought to look for. I only found it because the bar chart reacted to the airport filter.

{img("story_4_dtw_snowy_owl_radial.png", "Snowy owl strikes at DTW by month")}
""", images=["story_4_dtw_snowy_owl_radial.png"])
md("""
**Things that did not work out.** I wanted to compare how high geese get hit at DTW, but the ridgeline came up blank. Only 29% of DTW's reports include a height, which works out to a handful per species, so now the chart says that instead of drawing nothing. Only 32% of DTW reports fill in the damage field, so its damage rates come from a small subset. Repair cost would have been a better measure of harm, but only 1.5% of reports nationwide include it. And the national map did not point out dangerous airports. The big circles mostly show which airports file lots of reports, and busy airports actually have lower damage rates (Spearman correlation of minus 0.34 across airports with at least 100 reports).

**My answer.** Over the past 10 years, Canada geese have had very little impact on planes at Detroit Metro. They were 8 strikes out of 2,679, none in fall, and one minor damage report. That is not because geese are safe. Across the country they cause damage in about half of their strikes, and they peak right in late summer and fall. At DTW the damage instead comes from snowy owls in winter, hawks and gulls. The data cannot say why Detroit sees so few goose strikes. My guesses are the airport's wildlife management, or the geese I see simply using fields and ponds away from the runways, but I would need other data to check either one. A static chart of all strikes would have shown none of this. It only came out by filtering to one airport, one decade and one species at a time.
""")

# =====================================================================================
md("""
## 6. AI log and troubleshooting

I used Claude (in Claude Code) throughout and checked its work against the data, the live app and the library. Entries 3 and 4 are the problems.

**Entry 1. Evaluating data sources**
- Tool: Claude
- What I asked for / what I was trying to do: compare public datasets that could support four chart types, linked filters and a non-obvious finding.
- What came back / what happened: a shortlist (FAA wildlife strikes, Nobel laureates, Ember electricity data) with licenses, column richness and question ideas.
- What was wrong or could be better: it was not sure the FAA file was still downloadable, and one question it suggested (repair cost by species) only works for 1.5% of reports.
- How I noticed: I found the real "Download Excel" link on the FAA site and profiled how complete every column was.
- What I did instead: picked the FAA data and measured harm with damage level (65% complete) instead of cost.

**Entry 2. Hosting**
- Tool: Claude
- What I asked for / what I was trying to do: host the dashboard from my GitHub repo.
- What came back / what happened: it pointed out that GitHub Pages cannot run a Python server and set up Render with `render.yaml` instead.
- What was wrong or could be better: nothing broke, but the free plan has 512 MB of memory and two app workers would not fit.
- How I noticed: I measured the app at about 250 MB per process.
- What I did instead: run one worker with four threads.

**Entry 3. Chart rendering and wrong text**
- Tool: Claude
- What I asked for / what I was trying to do: build and title the six charts.
- What came back / what happened: four specific errors. A `responsive=True` setting squished every chart to a few pixels tall. The trend title said damaging strikes "do not" rise. The ridgeline hover box was hard to read and spilled outside the chart. And when I filtered to Detroit, the ridgeline went completely blank because no species had enough heights.
- What was wrong or could be better: the layout broke, the title was false (damaging strikes rose from about 486 to 719 a year, just slower than reports), and the hover was unusable.
- How I noticed: the first screenshot, my decade table, using the live app myself, and the Detroit screenshots.
- What I did instead: removed the setting, used a neutral title with the real numbers in the text, moved the hover to one dot per ridge at the median with a short white label, and made the ridgeline explain when there are too few heights to draw.

**Entry 4. No way to reset filters**
- Tool: Claude
- What I asked for / what I was trying to do: let people undo a filter on any chart.
- What came back / what happened: the first version only had one Reset all button, hid Plotly's toolbar, and showed the whole country on the map with no way to zoom.
- What was wrong or could be better: you could not clear just one chart's filter, and picking one airport (like Detroit Metro in Wayne County) out of a crowded national map was nearly impossible.
- How I noticed: clicking around the live dashboard.
- What I did instead: added a reset button under every chart (Show all years, Clear species, Clear airport), brought the toolbar back, and added scroll zoom, a Zoom to a state dropdown and a searchable Find an airport box to the map. The Playwright script tests every one of them.
""")

# =====================================================================================
md(f"""
## 7. Deployment

The code lives on GitHub at {REPO_URL}, and the app runs for free on **Render**, which builds it straight from that repo. A Python server cannot run on GitHub Pages, so I needed a host that actually runs Python. On the free plan the app goes to sleep after about 15 minutes with no visitors, so the first visit can take up to a minute to wake up.

Here is how to do it yourself.
1. Put the project on GitHub. The repo needs `app.py`, `charts.py`, `assets/`, `data/strikes_clean.parquet`, `requirements.txt` and `render.yaml`.
2. Sign up at render.com with your GitHub account, then click **New** and choose **Blueprint**.
3. Pick your repo. Render reads `render.yaml`, which tells it to install `requirements.txt` with Python 3.12 and start the app with `gunicorn app:server`. That is why `app.py` has the line `server = app.server`.
4. Click **Apply** and wait a few minutes for the first build. The app then shows up at a link like `https://wildlife-strikes-2zcv.onrender.com`. Render adds a random ending like `-2zcv` when the plain name is already taken, so check the link on your service page.
5. Open the link in a private window and click a bar, a ridgeline dot, an airport, the map zoom and a reset button to make sure everything works without installing anything.

I run only one worker with four threads, because each Python process uses about 250 MB and the free plan has 512 MB. Render is supposed to rebuild the app every time I push to GitHub, but at first my updates never showed up. If that happens, open the service on Render and use **Manual Deploy**, then **Deploy latest commit**, and make sure **Auto-Deploy** is on in the settings.

To run it on your own computer instead, use `pip install -r requirements.txt` and then `python app.py`, and open http://127.0.0.1:8050. To rebuild the data from scratch, install `requirements-notebook.txt` and run `python prepare_data.py`.
""")

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, OUT)
words = sum(len(re.sub(r"```.*?```|\|.*\|", "", c.source, flags=re.S).split()) for c in cells if c.cell_type == "markdown")
print("wrote", OUT, "cells", len(cells), "markdown words", words)
