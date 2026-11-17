# Wildlife Strikes Dashboard

How much do Canada geese affect planes at Detroit Metro? A linked Plotly + Dash dashboard of 360,000 FAA wildlife strike reports (1990 to 2026) with six charts that filter together by species, years and airport. The full story is in the notebook.

- **Live dashboard** https://wildlife-strikes-2zcv.onrender.com (may take a minute to wake up)
- **Video** YOUR-VIDEO-LINK
- **Notebook** [wildlife_strikes_dashboard.ipynb](wildlife_strikes_dashboard.ipynb) ([HTML](wildlife_strikes_dashboard.html))

![Dashboard](images/03_full_layout.png)

## Deploy your own

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sjain44/wildlife-strikes-dashboard)

## Data

[FAA National Wildlife Strike Database](https://wildlife.faa.gov/search). US government work, public domain.

## Built with

Plotly 7.1, Dash 4.5, pandas and gunicorn, hosted on Render. I used Claude to help with code and testing, and the notebook's AI log covers where it helped and where I had to fix its mistakes.
