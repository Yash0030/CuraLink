"""Browser automation tools (Tools 1, 2, 3) using Playwright.

Supports:
- Local Chromium mode and Browserbase cloud mode (region ap-southeast-1).
- Tool 1: ensure_logged_in (session expiration detection, CAPTCHA screenshot & human relay up to 3 attempts).
- Tool 2: list_reports (table for labA, cards for labB, paginated for labC, marks in_range).
- Tool 3: download_file (in-page fetch with base64 staging, expired session detection).
- Automatic portal reachability probe with fallback from port 3000 to port 8000.
- Cross-loop safe database call execution via safe_db_call helper.
"""

import base64
import logging
import asyncio
import socket
import re
import json
import urllib.request
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from app.config import settings
from app.portal_selectors import PORTAL_CONFIG
from app.tools.captcha_manager import CaptchaManager
from app.db.repository import Repository

logger = logging.getLogger("phr-organizer.browser")

def is_host_port_reachable(host: str, port: int, timeout: float = 1.5) -> bool:
    """Quick socket check to verify if a host and port are accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        res = sock.connect_ex((host, port))
        sock.close()
        return res == 0
    except Exception:
        return False

def get_effective_portal_base() -> str:
    """Determines the active portal base URL.
    Checks configured PORTAL_BASE_URL (e.g. https://zero-digital-labs.vercel.app).
    If an external HTTPS URL, uses it directly.
    If unreachable local URL, falls back to local backend port (http://127.0.0.1:8000).
    """
    configured = (settings.PORTAL_BASE_URL or "http://127.0.0.1:8000").rstrip("/")
    if configured.startswith("https://"):
        return configured

    parsed = urlparse(configured)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80

    if is_host_port_reachable(host, port, timeout=1.5):
        return configured

    # Try local fallback port 8000
    if host in ("127.0.0.1", "localhost") and is_host_port_reachable("127.0.0.1", 8000, timeout=1.0):
        logger.info(f"Configured portal base '{configured}' not reachable. Using local backend fallback: http://127.0.0.1:8000")
        return "http://127.0.0.1:8000"

    # Default to configured
    return configured

async def safe_db_call(coro, main_loop: Optional[Any] = None) -> Any:
    """Executes a database coroutine safely whether running on main loop or a worker thread."""
    if main_loop is None:
        return await coro
    try:
        curr_loop = asyncio.get_running_loop()
    except RuntimeError:
        curr_loop = None

    if curr_loop is not main_loop:
        return await asyncio.to_thread(lambda: asyncio.run_coroutine_threadsafe(coro, main_loop).result())
    return await coro

async def create_browser_session() -> Tuple[Any, Browser, BrowserContext, Page, Optional[str]]:
    """Creates a browser session either via local Playwright or Browserbase CDP."""
    logger.info("Initializing Playwright browser session...")
    p = await async_playwright().start()
    live_view_url = None

    if settings.BROWSER_MODE == "browserbase" and settings.BROWSERBASE_API_KEY:
        logger.info(f"Connecting to Browserbase CDP (region: {settings.BROWSERBASE_REGION})...")
        connect_url = None
        session_id = None
        try:
            req_data: Dict[str, Any] = {}
            if settings.BROWSERBASE_PROJECT_ID:
                req_data["projectId"] = settings.BROWSERBASE_PROJECT_ID
            req = urllib.request.Request(
                "https://api.browserbase.com/v1/sessions",
                data=json.dumps(req_data).encode(),
                headers={"X-BB-API-Key": settings.BROWSERBASE_API_KEY, "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                sess_data = json.loads(resp.read().decode())
                session_id = sess_data.get("id")
                connect_url = sess_data.get("connectUrl")
                if session_id:
                    live_view_url = f"https://browserbase.com/sessions/{session_id}"
                    logger.info(f"Created Browserbase session {session_id}. Live View: {live_view_url}")
        except Exception as e:
            logger.warning(f"Could not create Browserbase session via REST API ({e}). Falling back to direct CDP URL.")

        if not connect_url:
            connect_url = f"wss://connect.browserbase.com?apiKey={settings.BROWSERBASE_API_KEY}"
            if settings.BROWSERBASE_PROJECT_ID:
                connect_url += f"&projectId={settings.BROWSERBASE_PROJECT_ID}"
            live_view_url = "https://browserbase.com/sessions"

        browser = await p.chromium.connect_over_cdp(connect_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        logger.info(f"Connected to Browserbase successfully. Live view URL: {live_view_url}")
    else:
        # Local Chromium mode
        logger.info("Launching local Chromium browser in headless mode...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        logger.info("Local Chromium session initialized successfully.")

    return p, browser, context, page, live_view_url

async def ensure_logged_in(
    page: Page,
    lab: str,
    username: str,
    password: str,
    run_id: str,
    live_view_url: Optional[str] = None,
    main_loop: Optional[Any] = None
) -> bool:
    """Tool 1: Logs into the portal, recovers from expired sessions, and gates CAPTCHAs for human resolution."""
    config = PORTAL_CONFIG.get(lab)
    if not config:
        custom_cfg = await safe_db_call(Repository.get_lab_config(lab), main_loop)
        if custom_cfg:
            config = {
                "key": lab,
                "name": custom_cfg.get("name", lab),
                "layout": custom_cfg.get("layout", "table"),
                "has_captcha": custom_cfg.get("has_captcha", False),
                "login_path": "",
                "reports_path": "",
                "custom_url": custom_cfg.get("url", ""),
                "selectors": PORTAL_CONFIG["labA"]["selectors"]
            }
        else:
            raise ValueError(f"Unknown lab identifier: {lab}")

    selectors = config["selectors"]
    if config.get("custom_url"):
        login_url = config["custom_url"]
        reports_url = config["custom_url"]
    else:
        base_url = get_effective_portal_base()
        login_url = f"{base_url}{config['login_path']}"
        reports_url = f"{base_url}{config['reports_path']}"

    logger.info(f"[{lab}] Checking existing session or navigating to login page: {login_url}")

    # Check if session is already active
    try:
        await page.goto(reports_url, wait_until="networkidle", timeout=12000)
        if config["login_path"] in page.url or await page.query_selector(selectors["username_input"]):
            logger.info(f"[{lab}] No active session detected on {config['name']}. Proceeding to log in...")
        else:
            logger.info(f"[{lab}] Existing session is still valid for {config['name']}.")
            await safe_db_call(
                Repository.record_event(run_id, f"Fetcher-{lab}", "INFO", f"Reused active session on {config['name']}."),
                main_loop
            )
            return True
    except Exception as e:
        logger.info(f"[{lab}] Pre-login probe encountered: {e}. Navigating directly to login page.")
        await page.goto(login_url, wait_until="networkidle", timeout=15000)

    # Perform Login
    await safe_db_call(
        Repository.record_event(run_id, f"Fetcher-{lab}", "INFO", f"Navigating to login page for {config['name']} ({login_url})..."),
        main_loop
    )
    await page.goto(login_url, wait_until="domcontentloaded", timeout=15000)

    # Fill username and password
    masked_pw = "*" * len(password) if password else "empty"
    logger.info(f"[{lab}] Submitting credentials for {config['name']} (username='{username}', password={masked_pw})...")
    await page.fill(selectors["username_input"], username)
    await page.fill(selectors["password_input"], password)
    await page.click(selectors["submit_button"])
    try:
        await page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        await page.wait_for_timeout(1000)

    # Universal Dynamic CAPTCHA Detection:
    # Triggers if configured (has_captcha=True), OR if the page redirected to /captcha,
    # OR if any CAPTCHA challenge elements appear in the DOM (future-proofing labA).
    default_captcha_container = "form[action*='captcha'], .panel, #captcha-modal, .captcha-container, div[data-testid='captcha-modal']"
    default_captcha_image = "img[data-testid='captcha-image'], img[src*='captcha'], #captcha-image, .captcha-box img"
    default_captcha_input = "input#captcha-input, input[data-testid='captcha-input'], input[name='answer'], input[name='captcha']"
    default_captcha_submit = "button#captcha-submit, button[data-testid='captcha-submit'], button[type='submit'], button#verify-captcha"

    captcha_selector = selectors.get("captcha_container") or default_captcha_container
    image_selector = selectors.get("captcha_image") or default_captcha_image
    captcha_input_selector = selectors.get("captcha_input") or default_captcha_input
    captcha_submit_selector = selectors.get("captcha_submit") or default_captcha_submit

    on_captcha_url = "/captcha" in page.url
    has_captcha_elem = bool(await page.query_selector(image_selector) or await page.query_selector(captcha_selector))
    should_check_captcha = bool(config.get("has_captcha") or on_captcha_url or has_captcha_elem)

    if should_check_captcha:
        for attempt in range(1, 4):
            # Check if captcha container or image is present, or if current URL is /captcha
            on_captcha_url = "/captcha" in page.url
            captcha_elem = await page.query_selector(captcha_selector) if captcha_selector else None
            img_elem = await page.query_selector(image_selector) if image_selector else None

            if not on_captcha_url and not captcha_elem and not img_elem:
                logger.info(f"[{lab}] No CAPTCHA challenge detected on {config['name']}.")
                break

            # If element found, verify visibility
            if captcha_elem and not await captcha_elem.is_visible() and not on_captcha_url:
                logger.info(f"[{lab}] CAPTCHA container is not visible. Proceeding.")
                break

            logger.warning(f"[{lab}] CAPTCHA challenge detected on {config['name']} (attempt {attempt}/3). Pausing for human solver...")
            await safe_db_call(
                Repository.record_event(
                    run_id, f"Fetcher-{lab}", "WARNING",
                    f"CAPTCHA challenge detected on {config['name']} (attempt {attempt}/3). Waiting for human-in-the-loop input."
                ),
                main_loop
            )

            # Capture challenge screenshot
            if img_elem:
                screenshot_bytes = await img_elem.screenshot()
                logger.info(f"[{lab}] Captured CAPTCHA element screenshot ({len(screenshot_bytes)} bytes).")
            else:
                screenshot_bytes = await page.screenshot(full_page=False)
                logger.info(f"[{lab}] Captured viewport screenshot for CAPTCHA ({len(screenshot_bytes)} bytes).")

            # Register with in-memory CaptchaManager
            session = CaptchaManager.register(run_id, lab, screenshot_bytes, live_view_url)

            try:
                answer, solved_live = await CaptchaManager.wait_for_resolution(
                    session, timeout_seconds=settings.CAPTCHA_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                CaptchaManager.unregister(run_id, lab)
                logger.error(f"[{lab}] Human solver timed out on {config['name']} CAPTCHA.")
                await safe_db_call(
                    Repository.record_event(run_id, f"Fetcher-{lab}", "ERROR", f"CAPTCHA timeout on {config['name']}. Solver did not respond."),
                    main_loop
                )
                raise TimeoutError(f"Human did not solve CAPTCHA on {config['name']} within timeout.")

            CaptchaManager.unregister(run_id, lab)

            if solved_live:
                logger.info(f"[{lab}] CAPTCHA marked as solved directly in live view by user.")
                await page.wait_for_timeout(2000)
            elif answer:
                logger.info(f"[{lab}] Relaying human CAPTCHA answer '{answer}' into form...")
                await page.fill(captcha_input_selector, str(answer).strip())
                await page.click(captcha_submit_selector)
                try:
                    await page.wait_for_url(lambda u: config["reports_path"] in u or "/captcha" not in u, timeout=7000)
                except Exception:
                    await page.wait_for_timeout(2000)

            # Check if captcha container cleared or page redirected
            img_check = await page.query_selector(image_selector) if image_selector else None
            if config["reports_path"] in page.url or ("/captcha" not in page.url and not img_check):
                logger.info(f"[{lab}] CAPTCHA challenge successfully resolved on {config['name']}.")
                await safe_db_call(
                    Repository.record_event(run_id, f"Fetcher-{lab}", "INFO", f"CAPTCHA challenge cleared on {config['name']}."),
                    main_loop
                )
                break
            else:
                logger.warning(f"[{lab}] CAPTCHA still present after attempt {attempt}. Retrying...")
        else:
            raise RuntimeError(f"Failed to solve CAPTCHA on {config['name']} after 3 attempts.")

    # Confirm login success: navigation to reports or session indicator
    await page.wait_for_load_state("domcontentloaded")
    if config["login_path"] in page.url:
        err = await page.query_selector(selectors.get("error_message", ".alert-error"))
        err_text = (await err.inner_text()) if err else "Invalid credentials or login rejected"
        logger.error(f"[{lab}] Login failed on {config['name']}: {err_text}")
        raise RuntimeError(f"Login failed on {config['name']}: {err_text}")

    logger.info(f"[{lab}] Successfully logged into {config['name']}. Current URL: {page.url}")
    await safe_db_call(
        Repository.record_event(run_id, f"Fetcher-{lab}", "INFO", f"Successfully logged into {config['name']}."),
        main_loop
    )
    return True

async def list_reports(
    page: Page,
    lab: str,
    date_from: date,
    date_to: date,
    run_id: Optional[str] = None,
    main_loop: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """Tool 2: Lists reports across table, card, and paginated layouts, marking in_range."""
    config = PORTAL_CONFIG.get(lab)
    if not config:
        custom_cfg = await safe_db_call(Repository.get_lab_config(lab), main_loop)
        if custom_cfg:
            config = {
                "key": lab,
                "name": custom_cfg.get("name", lab),
                "layout": custom_cfg.get("layout", "table"),
                "has_captcha": custom_cfg.get("has_captcha", False),
                "login_path": "",
                "reports_path": "",
                "custom_url": custom_cfg.get("url", ""),
                "selectors": PORTAL_CONFIG["labA"]["selectors"]
            }
        else:
            raise ValueError(f"Unknown lab: {lab}")

    selectors = config["selectors"]
    layout = config["layout"]
    if config.get("custom_url"):
        reports_url = config["custom_url"]
    else:
        base_url = get_effective_portal_base()
        reports_url = f"{base_url}{config['reports_path']}"

    logger.info(f"[{lab}] Navigating to reports list ({layout} layout): {reports_url}")
    if config.get("custom_url"):
        if page.url != reports_url:
            await page.goto(reports_url, wait_until="networkidle", timeout=15000)
    elif not page.url.endswith(config["reports_path"]):
        await page.goto(reports_url, wait_until="networkidle", timeout=15000)

    reports = []

    def parse_report_date(raw_date_str: str) -> Optional[date]:
        if not raw_date_str:
            return None
        cleaned = re.sub(r"^(?:date\s*:\s*)", "", raw_date_str.strip(), flags=re.IGNORECASE).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        return None

    if layout == "table":
        # Table layout (labA / A1)
        logger.info(f"[{lab}] Waiting for table container '{selectors['table_container']}'...")
        await page.wait_for_selector(selectors["table_container"], timeout=10000)
        rows = await page.query_selector_all(selectors["table_rows"])
        logger.info(f"[{lab}] Found {len(rows)} table rows.")

        for idx, row in enumerate(rows):
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
            if not rep_id and href:
                m = re.search(r"([A-Z]-\d+-\d+-\d+)", href)
                if m:
                    rep_id = m.group(1)

            p_date = parse_report_date(date_str)
            in_range = bool(p_date and (date_from <= p_date <= date_to))

            logger.info(f"[{lab}] Row #{idx+1}: ID='{rep_id}', Title='{title}', Date='{date_str}' (parsed: {p_date}) -> in_range={in_range}")

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
        logger.info(f"[{lab}] Waiting for cards container '{selectors['cards_container']}'...")
        await page.wait_for_selector(selectors["cards_container"], timeout=10000)
        cards = await page.query_selector_all(selectors["card_item"])
        logger.info(f"[{lab}] Found {len(cards)} report cards.")

        for idx, card in enumerate(cards):
            rep_id_el = await card.query_selector(selectors["card_report_id"])
            title_el = await card.query_selector(selectors["card_title"])
            link_el = await card.query_selector(selectors["card_download_link"])

            rep_id = (await rep_id_el.inner_text()).strip() if rep_id_el else ""
            title = (await title_el.inner_text()).strip() if title_el else ""
            href = (await link_el.get_attribute("href")).strip() if link_el else ""

            date_str = ""
            date_el = await card.query_selector(selectors["card_date"])
            if date_el:
                date_str = (await date_el.inner_text()).strip()
            else:
                for p in await card.query_selector_all("p"):
                    p_txt = (await p.inner_text()).strip()
                    if "date" in p_txt.lower():
                        date_str = p_txt
                        break

            filename = href.split("/")[-1] if href else f"{rep_id}.pdf"
            if not rep_id and href:
                m = re.search(r"([A-Z]-\d+-\d+-\d+)", href)
                if m:
                    rep_id = m.group(1)

            p_date = parse_report_date(date_str)
            in_range = bool(p_date and (date_from <= p_date <= date_to))

            logger.info(f"[{lab}] Card #{idx+1}: ID='{rep_id}', Title='{title}', Date='{date_str}' (parsed: {p_date}) -> in_range={in_range}")

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
        logger.info(f"[{lab}] Loading paginated list layout...")
        page_num = 1
        max_pages = 20
        while page_num <= max_pages:
            await page.wait_for_selector(selectors["list_container"], timeout=10000)
            items = await page.query_selector_all(selectors["list_item"])
            logger.info(f"[{lab}] Paginated page {page_num}: found {len(items)} items.")

            for idx, item in enumerate(items):
                title_el = await item.query_selector(selectors["item_title"])
                link_el = await item.query_selector(selectors["item_download_link"])

                title = (await title_el.inner_text()).strip() if title_el else ""
                href = (await link_el.get_attribute("href")).strip() if link_el else ""

                rep_id = ""
                date_str = ""

                muted_el = await item.query_selector(".muted, [class*='muted']")
                if muted_el:
                    muted_text = (await muted_el.inner_text()).strip()
                    if "·" in muted_text:
                        parts = [p.strip() for p in muted_text.split("·")]
                        if len(parts) >= 2:
                            rep_id = parts[0]
                            date_str = parts[1]
                    else:
                        date_str = muted_text

                if not rep_id:
                    rep_id_el = await item.query_selector(selectors["item_report_id"])
                    if rep_id_el:
                        rep_id = (await rep_id_el.inner_text()).strip()
                if not date_str:
                    date_el = await item.query_selector(selectors["item_date"])
                    if date_el:
                        date_str = (await date_el.inner_text()).strip()

                if not rep_id and href:
                    m = re.search(r"([A-Z]-\d+-\d+-\d+)", href)
                    if m:
                        rep_id = m.group(1)

                filename = href.split("/")[-1] if href else f"{rep_id}.pdf"
                p_date = parse_report_date(date_str)
                in_range = bool(p_date and (date_from <= p_date <= date_to))

                logger.info(f"[{lab}] Page {page_num} Item #{idx+1}: ID='{rep_id}', Title='{title}', Date='{date_str}' (parsed: {p_date}) -> in_range={in_range}")

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
                is_disabled = (
                    await next_btn.get_attribute("disabled") is not None
                    or await next_btn.get_attribute("aria-disabled") == "true"
                    or "disabled" in (await next_btn.get_attribute("class") or "")
                )
                if is_disabled:
                    logger.info(f"[{lab}] Next page button disabled or aria-disabled; reached last page.")
                    break
                logger.info(f"[{lab}] Clicking next page ({page_num} -> {page_num+1})...")
                await next_btn.click()
                await page.wait_for_timeout(1000)
                page_num += 1
            else:
                logger.info(f"[{lab}] No next page button found; pagination finished.")
                break

    in_range_count = sum(1 for r in reports if r.get("in_range"))
    logger.info(f"[{lab}] Total reports listed: {len(reports)}, In-Range: {in_range_count}")
    return reports

async def download_file(
    page: Page,
    lab: str,
    filename: str,
    source_url: str,
    listing_title: str,
    portal_report_id: str,
    portal_date: Optional[date],
    run_id: str,
    main_loop: Optional[Any] = None
) -> Dict[str, Any]:
    """Tool 3: Fetches PDF via in-page fetch() with base64 staging, detecting session expiry."""
    config = PORTAL_CONFIG.get(lab)
    login_path = config["login_path"] if config else "/login"

    logger.info(f"[{lab}] Downloading report '{filename}' from {source_url} via in-page fetch...")

    # In-page fetch script to preserve logged-in cookies and credentials
    js_fetch = """
    async (url) => {
        try {
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
        } catch (e) {
            return { ok: false, status: 0, statusText: e.toString() };
        }
    }
    """

    res = await page.evaluate(js_fetch, source_url)

    if res.get("expired"):
        # Redirected to login => session expired!
        logger.warning(f"[{lab}] Session expired while attempting to download {filename}. Re-login needed.")
        return {
            "status": "session_expired",
            "message": "Session expired during file download. Needs re-login."
        }

    if not res.get("ok"):
        err_msg = f"Download failed with status {res.get('status')}: {res.get('statusText')}"
        logger.error(f"[{lab}] {err_msg}")
        raise RuntimeError(err_msg)

    raw_bytes = base64.b64decode(res["data"])
    content_type = res.get("contentType", "application/pdf")
    logger.info(f"[{lab}] Successfully downloaded '{filename}' ({len(raw_bytes)} bytes, content-type='{content_type}').")

    # Stage the file in Postgres
    candidate = await safe_db_call(
        Repository.save_candidate(
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
        ),
        main_loop
    )

    sha_short = candidate.get("sha256", "")[:8]
    logger.info(f"[{lab}] Staged candidate #{candidate['id']} in database (SHA-256: {sha_short}...).")

    await safe_db_call(
        Repository.record_event(
            run_id, f"Fetcher-{lab}", "INFO",
            f"Downloaded and staged '{filename}' ({len(raw_bytes)} bytes, SHA-256: {sha_short}..., Portal Date: {portal_date})."
        ),
        main_loop
    )

    return {
        "status": "staged",
        "candidate_id": candidate["id"],
        "filename": filename,
        "sha256": candidate.get("sha256"),
        "size_bytes": len(raw_bytes)
    }
