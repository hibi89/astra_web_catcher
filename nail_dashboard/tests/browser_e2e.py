"""Browser E2E smoke test for the local FastAPI demo.

Install: python -m pip install playwright && python -m playwright install chromium
Start: python -m uvicorn nail_dashboard.app:app --port 8010
Run: python -m nail_dashboard.tests.browser_e2e

Click handlers fetch data asynchronously, so wait for the resulting UI state.
"""
from __future__ import annotations

import re

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:8010/nails"
WAIT_MS = 15_000


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: errors.append(f"HTTP {response.status}: {response.url}")
            if "/api/nails/" in response.url and response.status >= 400
            else None,
        )
        rows = page.locator("#content tbody tr")
        try:
            page.goto(BASE, wait_until="domcontentloaded", timeout=WAIT_MS)
            expect(page.locator("#content .stat")).to_have_count(3, timeout=WAIT_MS)
            print("PASS dashboard: 3 KPI cards")

            page.locator('[data-view="tags"]').click()
            expect(page).to_have_url(re.compile(r"#v-tags$"), timeout=WAIT_MS)
            expect(rows).to_have_count(14, timeout=WAIT_MS)
            print("PASS tags: 14 rows")

            page.locator('[data-category="color"]').click()
            expect(rows).to_have_count(8, timeout=WAIT_MS)
            expect(page.locator('[data-category="color"]')).to_have_class(
                re.compile(r"\bactive\b"), timeout=WAIT_MS
            )
            print("PASS color: 8 rows")

            page.locator('[data-view="brand"]').click()
            expect(page).to_have_url(re.compile(r"#v-brand$"), timeout=WAIT_MS)
            expect(rows).to_have_count(4, timeout=WAIT_MS)
            print("PASS brands: global 4 rows")

            page.locator('[data-view="top"]').click()
            expect(page).to_have_url(re.compile(r"#v-top$"), timeout=WAIT_MS)
            expect(rows).to_have_count(15, timeout=WAIT_MS)
            print("PASS top posts: page 1 has 15 rows")

            page.locator('[data-page-move="next"]').click()
            expect(page).to_have_url(re.compile(r"[?&]page=2(?:&|#)"), timeout=WAIT_MS)
            expect(rows).to_have_count(5, timeout=WAIT_MS)
            print("PASS top posts: page 2 has 5 rows")

            page.locator('[data-brand="mellow"]').click()
            expect(page).to_have_url(re.compile(r"[?&]brand=mellow(?:&|#)"), timeout=WAIT_MS)
            expect(page).to_have_url(re.compile(r"[?&]page=1(?:&|#)"), timeout=WAIT_MS)
            expect(rows).to_have_count(15, timeout=WAIT_MS)
            expect(page.locator('[data-brand="mellow"]')).to_have_attribute(
                "aria-pressed", "true", timeout=WAIT_MS
            )
            print("PASS brand switch: page 1 has 15 rows")

            assert not errors, "Browser JS/API errors: " + "; ".join(errors)
            print("PASS browser E2E: four views, filters, pagination, brand reset and errors")
        except Exception:
            print("FAIL URL:", page.url)
            print("Current rows:", rows.count())
            print("Content preview:", page.locator("#content").inner_text()[:320])
            print("JS/API errors:", errors)
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
