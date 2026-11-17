"""Set the dashboard to the views used in the notebook's Detroit story and screenshot each one.

Usage: python scripts/story_shots.py [url]   (the app must already be running)
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8050"
OUT = Path(__file__).resolve().parent.parent / "images"


def settle(page):
    page.wait_for_timeout(600)
    page.wait_for_function("!document.querySelector('[data-dash-is-loading]')")
    page.wait_for_timeout(900)
    page.evaluate("window.scrollTo(0, 0)")


def kpis(page):
    return [page.inner_text(f"#{k}") for k in ("k-strikes", "k-damaging", "k-height", "k-night")]


def pick(page, dropdown_id, text):
    page.click(f"#{dropdown_id}")
    page.fill(".dash-dropdown-search", text)
    page.wait_for_timeout(400)
    page.locator("[role=option]", has_text=text).first.click()
    page.keyboard.press("Escape")
    settle(page)


def set_years(page, start, end):
    for box, value in zip(page.locator("#years input").all(), (start, end)):
        box.click()
        box.press("Control+a")
        box.type(str(value))
        box.press("Tab")  # the input commits on blur
        settle(page)


def card(page, graph_id, name):
    page.locator(f"#{graph_id}").locator("..").screenshot(path=OUT / name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    page.goto(URL)
    page.wait_for_selector("#sankey .sankey")
    settle(page)

    # 1. Detroit Metro, last 10 full years, every species
    set_years(page, 2016, 2025)
    pick(page, "airport-pick", "KDTW")
    print("DTW 2016-2025", kpis(page))
    page.screenshot(path=OUT / "story_1_dtw.png", full_page=True)
    card(page, "bar", "story_1_dtw_bar.png")
    card(page, "radial", "story_1_dtw_radial.png")

    # 2. ...only Canada geese
    pick(page, "species", "Canada goose")
    print("DTW Canada goose", kpis(page))
    page.screenshot(path=OUT / "story_2_dtw_goose.png", full_page=True)
    card(page, "trend", "story_2_dtw_goose_trend.png")

    # 3. Canada geese at every airport, map zoomed to Michigan
    page.click("#map ~ .card-footer .card-reset")
    settle(page)
    pick(page, "map-state", "Michigan")
    print("US Canada goose", kpis(page))
    page.screenshot(path=OUT / "story_3_us_goose.png", full_page=True)
    card(page, "radial", "story_3_us_goose_radial.png")
    card(page, "sankey", "story_3_us_goose_sankey.png")
    card(page, "map", "story_3_michigan_goose_map.png")

    # 4. what does damage planes at Detroit Metro? Snowy owls
    pick(page, "airport-pick", "KDTW")
    pick(page, "species", "Snowy owl")
    print("DTW snowy owl", kpis(page))
    card(page, "radial", "story_4_dtw_snowy_owl_radial.png")
    browser.close()
