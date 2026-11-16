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

LIVE_URL = "https://wildlife-strikes.onrender.com"
REPO_URL = "https://github.com/sjain44/wildlife-strikes-dashboard"
VIDEO_URL = "YOUR-VIDEO-LINK"

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

Every year pilots report around 20,000 times their plane hit a bird or some other animal. Most of the time nothing happens. So I got curious about the few strikes that actually do damage. Which animals cause them, and do they show up at the same time of year, at the same height and during the same part of the flight as all the harmless ones?

I built a dashboard to find out. You pick a species, a range of years or an airport, and six charts update together to tell you the story.

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
keep = ['Barn swallow', 'Mourning dove', 'Gulls', 'Canada goose', 'Turkey vulture', 'Snow goose']
air = df[df['airborne'] & df['species'].isin(keep)].copy()
air['species'] = air['species'].astype(str)
box = px.box(air, x='height_ft', y='species', log_x=True, points=False,
             category_orders={'species': keep[::-1]}, title='The usual way. Box plots of strike height')
box.update_traces(marker_color=C.BASE).update_layout(height=330, template='simple_white')
box.show()
""")
code("""
C.height_ridgeline(df, species='Snow goose').show()
""")
md("""
**Polar bars vs a line chart.** Snow goose strikes peak from November through January. On a normal January-to-December line, that peak gets cut in half, with one piece at the far left and the other at the far right. On the polar chart it stays in one piece, and you can see it sitting right on top of the summer peak for all other strikes.
""")
code("""
C.seasonal_radial(df, species='Snow goose').show()
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
    html.Div(className="grid", children=[card("trend", ...), card("radial", ...), card("bar", ...),
                                         card("ridge", ...), card("sankey", ...), card("map", ...)]),
])
```
""")

md("""
### Step 3. Linking the charts
The linking only takes two callbacks. The first one turns clicks into filter values. The second one takes those values and redraws everything.

| What you do | What updates |
| --- | --- |
| Pick a species in the dropdown | all six charts and all four numbers |
| Click a bar or a ridge | picks that species, so everything again |
| Drag the year slider | all six charts (the trend chart shades the years you picked) |
| Click an airport on the map | filters the other five charts to that airport |
| Hit Reset all | clears everything |

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

**The questions I started with.** Do strikes peak during migration, and is it the same peak for every animal? Which animals are rare but do a lot of the damage? Are strikes higher up worse? And if reports keep going up, does that mean flying is getting more dangerous?

**The rising line is mostly more reporting.** When I dragged the year slider from the 1990s to the 2020s, the number of reports went up about six times, from around 3,100 a year to 18,500 a year. Damaging strikes only went up about one and a half times, from 486 to 719 a year. The share of strikes that caused damage dropped from 19.2% to 6.5%. So airports are just reporting a lot more of the small stuff, and the rising line does not mean flying got more dangerous.
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
md("""
**Things that did not work out.** At first I wanted to use repair cost to measure harm, but it turns out only 1.5% of reports even fill it in, so I used the damage level instead (65% filled in). I also expected the map to point out dangerous airports. It did not. The big circles mostly show which airports file lots of reports, and the busy ones actually have lower damage rates (a Spearman correlation of minus 0.34 across airports with at least 100 reports). On top of that, 40% of reports do not name the species and half do not give a height, so each chart title says exactly what it includes.

**The finding I only got by clicking around.** Looking at all species together, the season peaks from July to September, the typical strike happens at 600 ft, 31% happen at night and 9.6% cause damage. Then I picked **Snow goose** in the dropdown and every chart changed at once.
""")
md(f"""
{img("04_snow_goose.png", "Snow goose selected")}
""", images=["04_snow_goose.png"])
code("""
def profile(sub):
    known = sub['damage'].ne('Not reported'); tod = sub['time_of_day'].ne('Not reported')
    months = sub['month'].value_counts(normalize=True)
    return {'reports': len(sub),
            'damaging share': f"{sub['damaging'].sum() / known.sum():.1%}",
            'median airborne height (ft)': sub.loc[sub['airborne'], 'height_ft'].median(),
            'at night': f"{sub['time_of_day'].eq('Night').sum() / tod.sum():.0%}",
            'Nov-Jan share': f"{months.reindex([11, 12, 1]).sum():.0%}",
            'Jul-Aug share': f"{months.reindex([7, 8]).fillna(0).sum():.0%}"}

pd.DataFrame({'All strikes': profile(df),
              'Snow goose': profile(df[df['species'].eq('Snow goose')]),
              'White-tailed deer': profile(df[df['species'].eq('White-tailed deer')]),
              'Brazilian free-tailed bat': profile(df[df['species'].eq('Brazilian free-tailed bat')])})
""")
md(f"""
Snow geese are only 0.06% of all reports, so they basically disappear in any chart of everything. Once I selected them, the polar chart flipped to winter, with 62% of their strikes from November to January and none at all in July or August. Their ridge jumped to the very top at a typical height of 2,000 ft. 73% of their strikes happen at night, and 77% cause damage. The map lit up California, Missouri, Tennessee and Nebraska, which sit right under big waterfowl migration routes. I never would have drawn a snow goose chart on purpose, because there are almost a thousand species in this data. The only reason I found it is that I could click around.

Comparing a few more animals showed me what is really going on. Deer cause damage 86% of the time, at a typical height of 4 ft, mostly at night while the plane is landing. Free-tailed bats get hit at night even more often (84%), but they cause damage only 1% of the time. So night and height are not dangerous on their own. Size is what matters, and the Sankey shows big animals feeding straight into the damage bands.

The map had one more surprise. Clicking Denver showed a second airport, `KDEN*`, sitting right on top of it. It is the old Stapleton airport. 91 of its 92 reports are from 1990 to 1994, and their 19% damage rate matches the early-years pattern from the trend chart. The last report is dated 2025, which has to be a typo, since Stapleton closed in 1995.

{img("06_airport_filter.png", "Airport filter")}
""", images=["06_airport_filter.png"])

# =====================================================================================
md("""
## 6. AI log and troubleshooting

I used Claude (in Claude Code) to help search for datasets, write the cleaning and chart code, and run a browser to test the app. I checked everything it gave me against the data, the screenshots and the library itself. All four entries below are about something that went wrong.

**Entry 1. Mixed-up column types broke the save**
- Tool: Claude
- What I asked for / what I was trying to do: turn the 159 MB Excel file into a parquet file so it loads quickly.
- What came back / what happened: a script that ended with `df.to_parquet(...)`.
- What was wrong or could be better: it crashed with `ArrowTypeError ... column AIRPORT_ID`, because that column has both numbers and text in it.
- How I noticed: the error message.
- What I did instead: turned every text column into a clean string before saving. That also fixed some extra spaces hiding in `AC_CLASS`.

**Entry 2. One setting squished every chart**
- Tool: Claude
- What I asked for / what I was trying to do: a first layout with six charts in a grid.
- What came back / what happened: every chart had `config={"responsive": True}`.
- What was wrong or could be better: that setting makes a chart fill the height of its box, and my boxes had no height, so all six charts ended up a few pixels tall.
- How I noticed: the first screenshot just showed squished titles.
- What I did instead: removed the setting so each chart uses its own height.

**Entry 3. A chart title that said too much**
- Tool: Claude
- What I asked for / what I was trying to do: a title for the trend chart that states the takeaway.
- What came back / what happened: "Reports keep rising. Damaging strikes do not."
- What was wrong or could be better: damaging strikes did rise, from about 486 to 719 a year. That is a lot slower than reports, but it is not flat, so the title was misleading. An earlier idea to compare repair costs had the same kind of problem, since only 1.5% of reports include a cost.
- How I noticed: I made the table by decade and the list of how complete each column is before writing this up.
- What I did instead: switched to a neutral title, put the real numbers in the text, and used damage level instead of cost.

**Entry 4. Old knowledge of the new Dash controls**
- Tool: Claude
- What I asked for / what I was trying to do: a test that picks a species and types in a year range.
- What came back / what happened: code that typed into the dropdown the old way and used `fill()` on the year box.
- What was wrong or could be better: Dash 4 replaced both controls. The dropdown now has its own search box, and the year box only updates when you click away. So nothing actually changed, but the test still passed.
- How I noticed: the printed numbers stayed stuck at 360,376.
- What I did instead: looked at the page's HTML, typed into `.dash-dropdown-search` and clicked the option, and pressed Tab after typing the year.
""")

# =====================================================================================
md(f"""
## 7. Deployment

The code lives on GitHub at {REPO_URL}, and the app runs for free on **Render**, which builds it straight from that repo. A Python server cannot run on GitHub Pages, so I needed a host that actually runs Python. On the free plan the app goes to sleep after about 15 minutes with no visitors, so the first visit can take up to a minute to wake up.

Here is how to do it yourself.
1. Put the project on GitHub. The repo needs `app.py`, `charts.py`, `assets/`, `data/strikes_clean.parquet`, `requirements.txt` and `render.yaml`.
2. Sign up at render.com with your GitHub account, then click **New** and choose **Blueprint**.
3. Pick your repo. Render reads `render.yaml`, which tells it to install `requirements.txt` with Python 3.12 and start the app with `gunicorn app:server`. That is why `app.py` has the line `server = app.server`.
4. Click **Apply** and wait a few minutes for the first build. The app then shows up at a link like `https://wildlife-strikes.onrender.com`.
5. Open the link in a private window and click a bar, a ridge and an airport to make sure everything works without installing anything.

I run only one worker with four threads, because each Python process uses about 250 MB and the free plan has 512 MB. Every time I push to GitHub, Render rebuilds the app automatically.

To run it on your own computer instead, use `pip install -r requirements.txt` and then `python app.py`, and open http://127.0.0.1:8050. To rebuild the data from scratch, install `requirements-notebook.txt` and run `python prepare_data.py`.
""")

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, OUT)
words = sum(len(re.sub(r"```.*?```|\|.*\|", "", c.source, flags=re.S).split()) for c in cells if c.cell_type == "markdown")
print("wrote", OUT, "cells", len(cells), "markdown words", words)
