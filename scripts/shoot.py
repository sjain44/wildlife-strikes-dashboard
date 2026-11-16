"""Drive the running dashboard in Edge, test the linked interactions and save screenshots.

Usage: python scripts/shoot.py [url]   (the app must already be running)
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8050"
OUT = Path(__file__).resolve().parent.parent / "images"
OUT.mkdir(exist_ok=True)


def settle(page):
    page.wait_for_timeout(600)
    page.wait_for_function("!document.querySelector('[data-dash-is-loading]')")
    page.wait_for_timeout(900)
    page.evaluate("window.scrollTo(0, 0)")  # keep the sticky control bar at the top of full-page shots


def kpis(page):
    return [page.inner_text(f"#{k}") for k in ("k-strikes", "k-damaging", "k-height", "k-night")]


def pick(page, dropdown_id, text):
    # Dash 4 dropdowns open a popover with their own search box
    page.click(f"#{dropdown_id}")
    page.fill(".dash-dropdown-search", text)
    page.wait_for_timeout(400)
    page.locator("[role=option]", has_text=text).first.click()
    page.keyboard.press("Escape")
    settle(page)


def pick_species(page, name):
    pick(page, "species", name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(URL)
    page.wait_for_selector("#sankey .sankey")
    settle(page)
    print("initial", kpis(page))
    page.screenshot(path=OUT / "03_full_layout.png", full_page=True)
    for gid in ("trend", "radial", "bar", "ridge", "sankey", "map"):
        page.locator(f"#{gid}").screenshot(path=OUT / f"02_chart_{gid}.png")

    # 1. dropdown -> every chart
    pick_species(page, "Snow goose")
    print("snow goose", kpis(page), page.locator("#species").inner_text())
    page.screenshot(path=OUT / "04_snow_goose.png", full_page=True)
    for gid in ("radial", "ridge"):
        page.locator(f"#{gid}").screenshot(path=OUT / f"05_snow_goose_{gid}.png")

    # 1b. hover a ridgeline median dot -> the label must stay inside the chart
    dot = page.locator("#ridge .scatterlayer .point").last
    dot.hover(force=True)
    page.wait_for_timeout(500)
    label = page.locator("#ridge .hoverlayer .hovertext").bounding_box()
    graph = page.locator("#ridge").bounding_box()
    inside = label and label["x"] >= graph["x"] and label["x"] + label["width"] <= graph["x"] + graph["width"]
    print("ridge hover label inside chart", bool(inside), page.locator("#ridge .hoverlayer").text_content().replace(chr(10), " | "))
    page.locator("#ridge").screenshot(path=OUT / "08_ridge_hover.png")

    # 1c. the polar chart's own reset button clears the species
    page.click("#radial ~ .card-footer .card-reset")
    settle(page)
    print("after polar card reset", kpis(page), page.locator("#species").inner_text())

    # 2. click a bar -> species changes (top bar = the most damaging species)
    bars = page.locator("#bar .trace.bars").nth(1).locator(".point path")
    bars.last.click(force=True)
    settle(page)
    print("after bar click", kpis(page), page.locator("#species").inner_text())

    # 3. click an airport -> airport filter
    page.click("#reset")
    settle(page)
    pts = page.locator("#map .scattergeo .point")
    print("map points", pts.count())
    pts.last.click(force=True)  # largest airport is drawn last
    settle(page)
    print("after map click", kpis(page), page.inner_text("#airport-chip"))
    page.screenshot(path=OUT / "06_airport_filter.png", full_page=True)
    page.click("#map ~ .card-footer .card-reset")
    settle(page)
    print("after map card reset", kpis(page), repr(page.inner_text("#airport-chip")))

    # 4. click a ridge -> species changes
    page.click("#reset")
    settle(page)
    page.locator("#ridge .scatterlayer .point").last.click(force=True)
    settle(page)
    print("after ridge click", kpis(page), page.locator("#species").inner_text())

    # 5. year range through the slider's input boxes
    page.click("#reset")
    settle(page)
    box = page.locator("#years input").first
    box.click()
    box.press("Control+a")
    box.type("2015")
    box.press("Tab")  # the input commits on blur
    settle(page)
    print("years 2015+", kpis(page))
    page.click("#trend ~ .card-footer .card-reset")
    settle(page)
    print("after trend card reset", kpis(page))
    page.click("#reset")
    settle(page)
    print("after reset", kpis(page))

    # 6. map tools: zoom to a state, find an airport, then clear both with the map's reset button
    pick(page, "map-state", "Michigan")
    print("zoom to Michigan", page.locator("#map .gtitle").text_content(), kpis(page))
    print("map zoom buttons", page.locator("#map .modebar-btn[data-title='Zoom in']").count(),
          page.locator("#map .modebar-btn[data-title='Zoom out']").count())
    page.locator("#map").screenshot(path=OUT / "09_map_michigan.png")
    pick(page, "airport-pick", "Detroit Metro")
    print("find Detroit", kpis(page), page.inner_text("#airport-chip"))
    page.locator("#map").locator("..").screenshot(path=OUT / "10_map_detroit.png")
    page.click("#map ~ .card-footer .card-reset")
    settle(page)
    print("map reset", kpis(page), repr(page.inner_text("#airport-chip")),
          page.locator("#map .gtitle").text_content())

    # 5. phone width
    page.set_viewport_size({"width": 390, "height": 844})
    settle(page)
    print("phone scroll width", page.evaluate("document.documentElement.scrollWidth"))
    page.screenshot(path=OUT / "07_phone.png", full_page=False)
    print("console errors", errors)
    browser.close()
