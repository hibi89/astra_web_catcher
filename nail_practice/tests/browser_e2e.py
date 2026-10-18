"""Run against a locally started 8011 server; user Windows Chrome Playwright.

Requires: pip install playwright; python -m playwright install chromium
Start server: python -m uvicorn nail_practice.app:app --port 8011
"""
from __future__ import annotations
import re
from playwright.sync_api import expect,sync_playwright

URL='http://127.0.0.1:8011/practice'


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:errors.append(f'HTTP {r.status} {r.url}') if '/api/practice/' in r.url and r.status>=400 else None)
        rows=page.locator('#content tbody tr')
        try:
            page.goto(URL,wait_until='domcontentloaded')
            expect(page.locator('#content .stat')).to_have_count(3,timeout=15000)
            print('PASS live DB dashboard 3 KPI cards')
            page.locator('[data-country="JP"]').first.click()
            expect(page).to_have_url(re.compile('country=JP'),timeout=15000)
            expect(page.locator('#rail-detail')).to_contain_text('910',timeout=15000)
            print('PASS country JP 910 posts')
            page.locator('[data-view="countries"]').click()
            expect(rows).to_have_count(3,timeout=15000)
            print('PASS countries: 3 rows')
            page.locator('[data-view="accounts"]').click()
            expect(rows).to_have_count(20,timeout=15000)
            page.locator('[data-status="failed"]').click()
            expect(rows).to_have_count(2,timeout=15000)  # JP has 2 failed accounts
            print('PASS JP account failures: 2 rows')
            page.locator('[data-view="posts"]').click()
            expect(rows).to_have_count(15,timeout=15000)
            page.locator('[data-page-move="next"]').click()
            expect(rows).to_have_count(5,timeout=15000)
            expect(page).to_have_url(re.compile('page=2'),timeout=15000)
            page.locator('[data-country="KR"]').first.click()
            expect(rows).to_have_count(15,timeout=15000)
            expect(page).to_have_url(re.compile('page=1'),timeout=15000)
            print('PASS posts 15+5 page and country change resets page 1')
            assert not errors,errors
            print('PASS real practice dashboard browser E2E')
        finally:
            browser.close()

if __name__=='__main__':main()
