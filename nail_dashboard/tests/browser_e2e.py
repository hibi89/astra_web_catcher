"""Run on an ordinary user's browser-enabled machine; blocked in the model sandbox.

Requires: pip install playwright && python -m playwright install chromium
Start server first: python -m uvicorn nail_dashboard.app:app --port 8010
"""
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8010/nails'

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(BASE,wait_until='domcontentloaded')
            page.locator('.stat').first.wait_for(timeout=10000)
            assert page.locator('.stat').count()==3
            page.locator('[data-view="tags"]').click()
            page.locator('tbody tr').first.wait_for()
            assert page.locator('tbody tr').count()==14
            page.locator('[data-category="color"]').click()
            assert page.locator('tbody tr').count()==8
            page.locator('[data-view="brand"]').click()
            assert page.locator('tbody tr').count()==4
            page.locator('[data-view="top"]').click()
            assert page.locator('tbody tr').count()==15
            page.locator('[data-page-move="next"]').click()
            assert page.locator('tbody tr').count()==5
            page.locator('[data-brand="mellow"]').click()
            assert page.locator('tbody tr').count()==15
            assert 'page=1' in page.url
            assert len(errors)==0,errors
            print('PASS browser four menus, color filter, compare, posts page 2, brand switch reset and JS console')
        finally: browser.close()

if __name__=='__main__':main()
