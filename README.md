# Which animals actually damage aircraft, and when?

Pilots report around 20,000 wildlife strikes a year, and almost all of them are harmless. This dashboard digs into the few that are not. It uses 360,000 strike reports from the FAA (1990 to 2026) and six linked charts, a line chart, a polar bar chart, a grouped bar chart, a ridgeline, a Sankey diagram and a map. Pick a species, drag the year range, or click a bar, a ridge or an airport, and everything updates together. The biggest surprise came from clicking around. Snow geese are only 0.06% of reports, but 77% of their strikes cause damage, and they happen in winter, at night and around 2,000 ft, while most strikes happen in summer near the ground.

- **Live dashboard** https://wildlife-strikes.onrender.com (free hosting, so the first load can take up to a minute)
- **Video walkthrough** YOUR-VIDEO-LINK
- **Narrative notebook** [`wildlife_strikes_dashboard.ipynb`](wildlife_strikes_dashboard.ipynb) (also as [HTML](wildlife_strikes_dashboard.html))

![Dashboard](images/03_full_layout.png)

## What's in here

| File | What it does |
| --- | --- |
| `app.py` | the Dash app, with the layout and the two callbacks that link the charts |
| `charts.py` | one function per chart, shared by the app and the notebook |
| `assets/style.css` | page styling, loaded by Dash automatically |
| `prepare_data.py` | downloads the raw FAA file and rebuilds the clean data |
| `data/strikes_clean.parquet` | the cleaned data the app reads (7 MB) |
| `wildlife_strikes_dashboard.ipynb` | the full write-up, covering library choice, data cleaning, chart choices, the build, findings and the AI log |
| `scripts/build_notebook.py` | rebuilds the notebook from the prose, `prepare_data.py` and the screenshots |
| `scripts/shoot.py` | opens the running app in a browser, tests every linked control and saves screenshots |
| `images/` | screenshots used in the notebook and this README |
| `requirements.txt` | what the app needs to run |
| `requirements-notebook.txt` | extra packages for rebuilding the data and the notebook |
| `render.yaml` | hosting setup for Render |

## The data and its license

The data comes from the [FAA National Wildlife Strike Database](https://wildlife.faa.gov/search), using the "Download Excel" button (a 133 MB zip downloaded on 16 November 2026). It is a work of the US federal government, so it is in the **public domain**, and the FAA already removes the names of the people who filed reports. Reporting is voluntary, so the counts are reports, not every strike that happened. The raw download is not in this repo because of its size. `python prepare_data.py` downloads it again and rebuilds `data/strikes_clean.parquet`.

## Run it yourself

```bash
python -m venv .venv
.venv/Scripts/activate        # on macOS/Linux use: source .venv/bin/activate
pip install -r requirements.txt
python app.py                 # then open http://127.0.0.1:8050
```

To rebuild the data and the notebook, run `pip install -r requirements-notebook.txt`, then `python prepare_data.py`, then `python scripts/build_notebook.py`.

## Hosting

A Dash app needs a Python server, so it cannot run on GitHub Pages. It runs on [Render](https://render.com) instead.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sjain44/wildlife-strikes-dashboard)

Click the button (or on Render choose **New**, then **Blueprint**, and pick this repo). `render.yaml` handles the rest, and every push to `main` redeploys the app.

## Built with

Plotly 7.1 and Dash 4.5, pandas, and gunicorn. I used Claude to help write code and test the app. The notebook's AI log describes where it helped and where I had to fix its mistakes.
