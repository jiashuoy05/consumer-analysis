import os
import re
import csv
import io
import base64
import calendar
from datetime import date
from io import BytesIO
from typing import Optional
from pathlib import Path

from playwright.async_api import async_playwright, Page
from playwright_stealth import Stealth
from PIL import Image
import numpy as np
import ddddocr


_ocr: Optional[ddddocr.DdddOcr] = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = ddddocr.DdddOcr(show_ad=False)
    return _ocr


async def login_and_scrape(
    phone: str, password: str, headless: bool = True,
    start_year: str = "", start_month: str = "",
    end_year: str = "", end_month: str = "",
) -> dict:
    """Login to e-invoice portal, scrape carrier id and invoice data.

    Scrapes invoices month by month from start_year/start_month to end_year/end_month.
    Defaults to last 3 months if no dates given.
    """
    ocr = _get_ocr()
    all_rows = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900},
            locale="zh-TW",
            accept_downloads=True,
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        # Login
        await _login(page, phone, password, ocr)

        # Navigate to search page
        await page.goto(
            "https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search",
            wait_until="networkidle", timeout=60000,
        )
        await page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            raise Exception("登入失敗，請檢查帳號密碼")

        await page.wait_for_timeout(3000)

        # Extract 手機條碼 and E-mail from the search page
        carrier_id = ""
        email = ""
        phone_from_page = ""

        login_info = await page.query_selector("div.login_info")
        if login_info:
            phone_el = await login_info.query_selector("li.phone span")
            if phone_el:
                phone_from_page = (await phone_el.inner_text()).strip()

            carrier_el = await login_info.query_selector("a.copy_tip")
            if carrier_el:
                carrier_text = await carrier_el.inner_text()
                m = re.search(r"/[A-Z0-9\-]{7,9}", carrier_text)
                if m:
                    carrier_id = m.group()

            mail_el = await login_info.query_selector("li.mail span")
            if mail_el:
                email = (await mail_el.inner_text()).strip()
                email = re.sub(r"\s*\(.*?\)\s*", "", email)

        # Build list of months to scrape
        today = date.today()
        s_year = int(start_year) if start_year else today.year
        s_month = int(start_month) if start_month else today.month - 2
        e_year = int(end_year) if end_year else today.year
        e_month = int(end_month) if end_month else today.month

        while s_month <= 0:
            s_month += 12
            s_year -= 1
        if e_year > today.year or (e_year == today.year and e_month > today.month):
            e_year = today.year
            e_month = today.month

        months = []
        y, m = s_year, s_month
        while (y, m) <= (e_year, e_month):
            months.append((y, m))
            m += 1
            if m > 12:
                m = 1
                y += 1

        if not months:
            months = [(today.year, today.month)]

        debug_dir = Path(os.environ.get("TEMP", "."))

        for month_idx, (target_y, target_m) in enumerate(months):
            if month_idx > 0:
                # Navigate back to search page for next month
                await page.goto(
                    "https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search",
                    wait_until="networkidle", timeout=60000,
                )
                await page.wait_for_timeout(3000)

            # Open datepicker
            await page.evaluate('document.getElementById("dp-input-searchInvoiceDate").click()')
            await page.wait_for_timeout(2000)

            arrows = await page.query_selector_all("button.dp--arrow-btn-nav")

            # Navigate from today to target month
            target_diff = (today.year - target_y) * 12 + (today.month - target_m)
            if target_diff > 0 and arrows:
                for remaining in range(target_diff, 0, -1):
                    if not await arrows[0].is_enabled():
                        cur_y = target_y
                        cur_m = target_m + remaining
                        while cur_m > 12:
                            cur_m -= 12
                            cur_y += 1
                        raise Exception(
                            f"月份 {target_y}/{target_m} 超出可查詢範圍，"
                            f"最早只能查到 {cur_y}/{cur_m}"
                        )
                    await page.evaluate('el => el.click()', arrows[0])
                    await page.wait_for_timeout(500)
                await page.wait_for_timeout(1500)

            # Select first day
            day1_id = f"{target_y}-{target_m:02d}-01"
            day1 = await page.query_selector(f'[id="{day1_id}"]')
            if day1:
                await page.evaluate('el => el.click()', day1)
                await page.wait_for_timeout(1000)

            # Select last day
            last_day = calendar.monthrange(target_y, target_m)[1]
            day_last_id = f"{target_y}-{target_m:02d}-{last_day:02d}"
            day_last = await page.query_selector(f'[id="{day_last_id}"]')
            if day_last:
                await page.evaluate('el => el.click()', day_last)
                await page.wait_for_timeout(1000)

            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

            # Set rows per page to 100
            select = await page.query_selector("#SelectSizes")
            if select:
                await select.select_option("100")
                await page.wait_for_timeout(2000)

            # Search
            query_btn = await page.query_selector('button:has-text("查詢")')
            if query_btn:
                await query_btn.scroll_into_view_if_needed()
                await page.evaluate('el => el.click()', query_btn)
                await page.wait_for_timeout(10000)

            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(debug_dir / f"scraper_m{target_y}_{target_m}.png"))

            # Download CSV pages
            page_no = 1
            while True:
                all_cb = await page.query_selector('input#invoiceDetailAll[type="checkbox"]')
                if all_cb:
                    await page.evaluate('el => el.click()', all_cb)
                    await page.wait_for_timeout(2000)

                dl_btn = await page.query_selector('button[title="下載CSV檔"]')
                if dl_btn:
                    is_disabled = await dl_btn.is_disabled()
                    if not is_disabled:
                        try:
                            async with page.expect_download(timeout=30000) as dl_info:
                                await page.evaluate('el => el.click()', dl_btn)
                            download = await dl_info.value
                            dl_path = await download.path()
                            if dl_path:
                                with open(dl_path, "rb") as f:
                                    csv_content = f.read()
                                parsed = _parse_csv(csv_content)
                                all_rows.extend(parsed)
                        except Exception as e:
                            await page.screenshot(
                                path=str(debug_dir / f"dl_fail_m{target_y}_{target_m}_p{page_no}.png")
                            )

                next_btn = await page.query_selector(
                    'li.page-item a.page-link[title="下一頁"]:not([disabled])'
                )
                if not next_btn:
                    break

                await page.evaluate('el => el.click()', next_btn)
                await page.wait_for_timeout(5000)
                page_no += 1

        await page.screenshot(path=str(debug_dir / "scraper_done.png"))
        await browser.close()

    all_rows.sort(key=lambda r: r.get("invDate", ""))
    return {"invoices": all_rows, "carrier_id": carrier_id, "email": email, "phone": phone_from_page}


async def _login(page: Page, phone: str, password: str, ocr) -> None:
    for attempt in range(3):
        await page.goto(
            "https://www.einvoice.nat.gov.tw/accounts/login/mw",
            wait_until="networkidle", timeout=60000,
        )
        await page.wait_for_timeout(5000)

        captcha_img = await page.query_selector('img[alt*="驗證"]')
        if not captcha_img:
            raise Exception("Captcha image not found")

        src = await captcha_img.get_attribute("src")
        arr = np.array(Image.open(BytesIO(base64.b64decode(src.split(",", 1)[1]))))
        alpha = Image.fromarray(arr[:, :, 3], mode="L")
        buf = BytesIO()
        alpha.save(buf, format="PNG")
        captcha_text = ocr.classification(buf.getvalue())

        await page.fill("#mobile_phone", phone)
        await page.fill("#password", password)
        await page.fill("#captcha", captcha_text)
        await page.wait_for_timeout(1000)
        await page.wait_for_function(
            "document.getElementById('submitBtn') && !document.getElementById('submitBtn').disabled",
            timeout=10000,
        )
        await page.evaluate('document.getElementById("submitBtn").click()')

        try:
            await page.wait_for_url("**/btc/**", timeout=20000)
            await page.wait_for_timeout(3000)
            return
        except:
            pass

    raise Exception("登入失敗，請檢查帳號密碼")


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        norm = {}
        for k, v in row.items():
            key = k.strip() if k else ""
            if isinstance(v, list):
                val = v[0].strip() if v and v[0] else ""
            else:
                val = v.strip() if v else ""
            norm[key] = val
        rows.append({
            "invNum": norm.get("發票號碼", ""),
            "invDate": norm.get("發票日期", ""),
            "description": norm.get("消費明細_品名", norm.get("明細資料_品名", norm.get("品名", norm.get("商品名稱", "")))),
            "quantity": norm.get("消費明細_數量", norm.get("明細資料_數量", norm.get("數量", ""))),
            "unitPrice": norm.get("消費明細_單價", norm.get("明細資料_單價", norm.get("單價", ""))),
            "amount": norm.get("消費明細_金額", norm.get("明細資料_金額", norm.get("金額", norm.get("金額(小計)", "")))),
            "sellerName": norm.get("賣方名稱", ""),
        })
    return [r for r in rows if r["invNum"]]


async def validate_login(
    phone: str, password: str, headless: bool = True
) -> dict:
    """Quick login to verify credentials and extract user info."""
    ocr = _get_ocr()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 900},
            locale="zh-TW",
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        await _login(page, phone, password, ocr)

        await page.goto(
            "https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search",
            wait_until="networkidle", timeout=60000,
        )
        await page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            raise Exception("登入失敗，請檢查帳號密碼")

        login_info = await page.query_selector("div.login_info")
        carrier_id = ""
        email = ""
        phone_from_page = ""
        if login_info:
            phone_el = await login_info.query_selector("li.phone span")
            if phone_el:
                phone_from_page = (await phone_el.inner_text()).strip()
            carrier_el = await login_info.query_selector("a.copy_tip")
            if carrier_el:
                carrier_text = await carrier_el.inner_text()
                m = re.search(r"/[A-Z0-9\-]{7,9}", carrier_text)
                if m:
                    carrier_id = m.group()
            mail_el = await login_info.query_selector("li.mail span")
            if mail_el:
                email_text = (await mail_el.inner_text()).strip()
                email = re.sub(r"\s*\(.*?\)\s*", "", email_text)

        await browser.close()

    return {"carrier_id": carrier_id, "email": email, "phone": phone_from_page}
