"""Browser automation tools (Tools 1, 2, 3) using Playwright.

Supports:
- Local Chromium mode and Browserbase cloud mode (region ap-southeast-1).
- Tool 1: ensure_logged_in (session expiration detection, CAPTCHA screenshot & human relay up to 3 attempts).
- Tool 2: list_reports (table for labA, cards for labB, paginated for labC, marks in_range).
- Tool 3: download_file (in-page fetch with base64 staging, expired session detection).
"""

import base64
import logging
import asyncio
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from app.config import settings
from app.portal_selectors import PORTAL_CONFIG
from app.tools.captcha_manager import CaptchaManager
from app.db.repository import Repository

logger = logging.getLogger(__name__)

async def create_browser_session() -> Tuple[Any, Browser, BrowserContext, Page, Optional[str]]:
    """Creates a browser session either via local Playwright or Browserbase CDP."""
    p = await async_playwright().start()
    live_view_url = None

    if settings.BROWSER_MODE == "browserbase" and settings.BROWSERBASE_API_KEY:
        logger.info(f"Connecting to Browserbase in region {settings.BROWSERBASE_REGION}...")
        cdp_url = f"wss://connect.browserbase.com?apiKey={settings.BROWSERBASE_API_KEY}"
        if settings.BROWSERBASE_PROJECT_ID:
            cdp_url += f"&projectId={settings.BROWSERBASE_PROJECT_ID}"
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        # Browserbase debug live view URL format
        live_view_url = "https://browserbase.com/sessions"
    else:
        # Local Chromium mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

    return p, browser, context, page, live_view_url

async def ensure_logged_in(
    page: Page,
    lab: str,
    username: str,
    password: str,
    run_id: str,
    live_view_url: Optional[str] = None
) -> bool:
    """Tool 1: Logs into the portal, recovers from expired sessions, and gates CAPTCHAs for human resolution."""
    config = PORTAL_CONFIG.get(lab)
    if not config:
        raise ValueError(f"Unknown lab: {lab}")

    selectors = config["selectors"]
    base_url = settings.PORTAL_BASE_URL.rstrip("/")
    login_url = f"{base_url}{config['login_path']}"
    reports_url = f"{base_url}{config['reports_path']}"

    # Check current URL or navigate to reports to see if session is still active
    try:
        await page.goto(reports_url, wait_until="networkidle", timeout=15000)
        # If redirected to login or login form visible, session expired or not logged in
        if config["login_path"] in page.url or await page.query_selector(selectors["username_input"]):
            logger.info(f"[{lab}] Session not active or expired. Proceeding to login...")
        else:
            logger.info(f"[{lab}] Existing session is still active.")
            return True
    except Exception:
        await page.goto(login_url, wait_until="networkidle", timeout=15000)

    # Perform Login
    await Repository.record_event(run_id, f"Fetcher-{lab}", "INFO", f"Navigating to login page for {config['name']}...")
    await page.goto(login_url, wait_until="domcontentloaded", timeout=15000)

    # Fill username and password
    await page.fill(selectors["username_input"], username)
    await page.fill(selectors["password_input"], password)
    await page.click(selectors["submit_button"])
    await page.wait_for_timeout(1000)

    # Check for CAPTCHA if this lab requires it
    if config["has_captcha"]:
        captcha_selector = selectors.get("captcha_container")
        image_selector = selectors.get("captcha_image")

        for attempt in range(1, 4):
            # Check if captcha container is present
            captcha_elem = await page.query_selector(captcha_selector) if captcha_selector else None
            if not captcha_elem:
                break  # No captcha or already solved

            logger.info(f"[{lab}] CAPTCHA detected (attempt {attempt}/3). Pausing for human solver...")
            await Repository.record_event(
                run_id, f"Fetcher-{lab}", "WARNING",
                f"CAPTCHA challenge detected on {config['name']} (attempt {attempt}/3). Waiting for human input."
            )

            # Capture challenge screenshot
            img_elem = await page.query_selector(image_selector)
            if img_elem:
                screenshot_bytes = await img_elem.screenshot()
            else:
                screenshot_bytes = await page.screenshot(full_page=False)

            # Register with in-memory CaptchaManager
            session = CaptchaManager.register(run_id, lab, screenshot_bytes, live_view_url)

            try:
                answer, solved_live = await CaptchaManager.wait_for_resolution(
                    session, timeout_seconds=settings.CAPTCHA_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                CaptchaManager.unregister(run_id, lab)
                await Repository.record_event(run_id, f"Fetcher-{lab}", "ERROR", f"CAPTCHA timeout on {config['name']}.")
                raise TimeoutError(f"Human did not solve CAPTCHA on {config['name']} within timeout.")

            CaptchaManager.unregister(run_id, lab)

            if solved_live:
                logger.info(f"[{lab}] User solved CAPTCHA in live view.")
                await page.wait_for_timeout(2000)
            elif answer:
                logger.info(f"[{lab}] Relaying human CAPTCHA answer: '{answer}'")
                await page.fill(selectors["captcha_input"], answer)
                await page.click(selectors["captcha_submit"])
                await page.wait_for_timeout(1500)

            # Verify if captcha cleared
            if not await page.query_selector(captcha_selector):
                logger.info(f"[{lab}] CAPTCHA challenge successfully resolved.")
                await Repository.record_event(run_id, f"Fetcher-{lab}", "INFO", f"CAPTCHA challenge cleared on {config['name']}.")
                break
        else:
            raise RuntimeError(f"Failed to solve CAPTCHA on {config['name']} after 3 attempts.")

    # Confirm login success: navigation to reports or session indicator
    await page.wait_for_load_state("domcontentloaded")
    if config["login_path"] in page.url:
        err = await page.query_selector(selectors.get("error_message", ".alert-error"))
        err_text = (await err.inner_text()) if err else "Login failed"
        raise RuntimeError(f"Login failed on {config['name']}: {err_text}")

    await Repository.record_event(run_id, f"Fetcher-{lab}", "INFO", f"Successfully logged into {config['name']}.")
    return True

async def list_reports(
    page: Page,
    lab: str,
    date_from: date,
    date_to: date
) -> List[Dict[str, Any]]:
    """Tool 2: Lists reports across table, card, and paginated layouts, marking in_range."""
    config = PORTAL_CONFIG.get(lab)
    if not config:
        raise ValueError(f"Unknown lab: {lab}")

    selectors = config["selectors"]
    layout = config["layout"]
    base_url = settings.PORTAL_BASE_URL.rstrip("/")
    reports_url = f"{base_url}{config['reports_path']}"

    # Navigate to reports page if not already there
    if not page.url.endswith(config["reports_path"]):
        await page.goto(reports_url, wait_until="networkidle", timeout=15000)

    reports = []

    def parse_report_date(raw_date_str: str) -> Optional[date]:
        if not raw_date_str:
            return None
        raw_date_str = raw_date_str.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(raw_date_str, fmt).date()
            except ValueError:
                continue
        return None

    if layout == "table":
        # Table layout (labA / A1)
        await page.wait_for_selector(selectors["table_container"], timeout=10000)
        rows = await page.query_selector_all(selectors["table_rows"])
        for row in rows:
            rep_id_el = await row.query_selector(selectors["row_report_id"])
            title_el = await row.query_selector(selectors["row_title"])
            date_el = await row.query_selector(selectors["row_date"])
            link_el = await row.query_selector(selectors["row_download_link"])

            rep_id = (await rep_id_el.inner_text()).strip() if rep_id_el else ""
            title = (await title_el.inner_text()).strip() if title_el else ""
            date_str = (await date_el.inner_text()).strip() if date_el else ""
            href = (await link_el.get_attribute("href")).strip() if link_el else ""

            if not href and not rep_id:
                continue

            filename = href.split("/")[-1] if href else f"{rep_id}.pdf"
            p_date = parse_report_date(date_str)
            in_range = bool(p_date and (date_from <= p_date <= date_to))

            reports.append({
                "lab": lab,
                "filename": filename,
                "title": title,
                "report_id": rep_id,
                "portal_date": p_date,
                "in_range": in_range,
                "download_url": urljoin(page.url, href) if href else f"{base_url}/labA/download/{filename}"
            })

    elif layout == "cards":
        # Cards layout (labB / CityScan Imaging)
        await page.wait_for_selector(selectors["cards_container"], timeout=10000)
        cards = await page.query_selector_all(selectors["card_item"])
        for card in cards:
            rep_id_el = await card.query_selector(selectors["card_report_id"])
            title_el = await card.query_selector(selectors["card_title"])
            date_el = await card.query_selector(selectors["card_date"])
            link_el = await card.query_selector(selectors["card_download_link"])

            rep_id = (await rep_id_el.inner_text()).strip() if rep_id_el else ""
            title = (await title_el.inner_text()).strip() if title_el else ""
            date_str = (await date_el.inner_text()).strip() if date_el else ""
            href = (await link_el.get_attribute("href")).strip() if link_el else ""

            filename = href.split("/")[-1] if href else f"{rep_id}.pdf"
            p_date = parse_report_date(date_str)
            in_range = bool(p_date and (date_from <= p_date <= date_to))

            reports.append({
                "lab": lab,
                "filename": filename,
                "title": title,
                "report_id": rep_id,
                "portal_date": p_date,
                "in_range": in_range,
                "download_url": urljoin(page.url, href) if href else f"{base_url}/labB/download/{filename}"
            })

    elif layout == "paginated":
        # Paginated list layout (labC / Vitals, 3 per page)
        page_num = 1
        max_pages = 20
        while page_num <= max_pages:
            await page.wait_for_selector(selectors["list_container"], timeout=10000)
            items = await page.query_selector_all(selectors["list_item"])
            for item in items:
                rep_id_el = await item.query_selector(selectors["item_report_id"])
                title_el = await item.query_selector(selectors["item_title"])
                date_el = await item.query_selector(selectors["item_date"])
                link_el = await item.query_selector(selectors["item_download_link"])

                rep_id = (await rep_id_el.inner_text()).strip() if rep_id_el else ""
                title = (await title_el.inner_text()).strip() if title_el else ""
                date_str = (await date_el.inner_text()).strip() if date_el else ""
                href = (await link_el.get_attribute("href")).strip() if link_el else ""

                filename = href.split("/")[-1] if href else f"{rep_id}.pdf"
                p_date = parse_report_date(date_str)
                in_range = bool(p_date and (date_from <= p_date <= date_to))

                reports.append({
                    "lab": lab,
                    "filename": filename,
                    "title": title,
                    "report_id": rep_id,
                    "portal_date": p_date,
                    "in_range": in_range,
                    "download_url": urljoin(page.url, href) if href else f"{base_url}/labC/download/{filename}"
                })

            # Check for next page button
            next_btn = await page.query_selector(selectors["next_page_btn"])
            if next_btn:
                is_disabled = await next_btn.get_attribute("disabled")
                if is_disabled:
                    break
                await next_btn.click()
                await page.wait_for_timeout(1000)
                page_num += 1
            else:
                break

    return reports

async def download_file(
    page: Page,
    lab: str,
    filename: str,
    source_url: str,
    listing_title: str,
    portal_report_id: str,
    portal_date: Optional[date],
    run_id: str
) -> Dict[str, Any]:
    """Tool 3: Fetches PDF via in-page fetch() with base64 staging, detecting session expiry."""
    config = PORTAL_CONFIG.get(lab)
    login_path = config["login_path"] if config else "/login"

    # In-page fetch script to preserve logged-in cookies and credentials
    js_fetch = """
    async (url) => {
        const response = await fetch(url, { credentials: 'include' });
        if (response.redirected && response.url.includes('""" + login_path + """')) {
            return { expired: true, status: response.status };
        }
        if (!response.ok) {
            return { ok: false, status: response.status, statusText: response.statusText };
        }
        const blob = await response.blob();
        const reader = new FileReader();
        return new Promise((resolve) => {
            reader.onloadend = () => {
                const base64data = reader.result.split(',')[1];
                resolve({
                    ok: true,
                    status: response.status,
                    contentType: response.headers.get('content-type') || 'application/pdf',
                    data: base64data
                });
            };
            reader.readAsDataURL(blob);
        });
    }
    """

    res = await page.evaluate(js_fetch, source_url)

    if res.get("expired"):
        # Redirected to login => session expired!
        logger.warning(f"[{lab}] Session expired while attempting to download {filename}.")
        return {
            "status": "session_expired",
            "message": "Session expired during file download. Needs re-login."
        }

    if not res.get("ok"):
        raise RuntimeError(f"Download failed with status {res.get('status')}: {res.get('statusText')}")

    raw_bytes = base64.b64decode(res["data"])
    content_type = res.get("contentType", "application/pdf")

    # Stage the file in Postgres
    candidate = await Repository.save_candidate(
        run_id=run_id,
        lab=lab,
        filename=filename,
        source_url=source_url,
        listing_title=listing_title,
        portal_report_id=portal_report_id,
        portal_date=portal_date,
        file_bytes=raw_bytes,
        http_status=res.get("status", 200),
        content_type=content_type
    )

    await Repository.record_event(
        run_id, f"Fetcher-{lab}", "INFO",
        f"Downloaded and staged '{filename}' ({len(raw_bytes)} bytes, SHA-256: {candidate.get('sha256')[:8]}...)."
    )

    return {
        "status": "staged",
        "candidate_id": candidate["id"],
        "filename": filename,
        "sha256": candidate.get("sha256"),
        "size_bytes": len(raw_bytes)
    }
