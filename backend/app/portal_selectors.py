"""Portal CSS selectors configuration.

Central configuration file for all lab portal layouts, selectors, and credentials.
Supports:
- labA (A1): Table layout
- labB (CityScan Imaging): Card layout with CAPTCHA
- labC (Vitals): Paginated list layout (3 per page) with CAPTCHA
"""

from typing import Dict, Any

PORTAL_CONFIG: Dict[str, Dict[str, Any]] = {
    "labA": {
        "key": "labA",
        "name": "A1",
        "layout": "table",
        "has_captcha": False,
        "login_path": "/labA/login",
        "reports_path": "/labA/reports",
        "download_path": "/labA/download/{filename}",
        "selectors": {
            # Login Form
            "username_input": "input#username, input[name='username'], input[type='text']",
            "password_input": "input#password, input[name='password'], input[type='password']",
            "submit_button": "button[type='submit'], button#login-btn, .login-button",
            "error_message": ".alert-error, .login-error, #error-message",
            "session_indicator": ".user-profile, #logout-btn, a[href*='logout'], table.reports-table",

            # Table Layout Selectors
            "table_container": "table#reports-table, table.reports-table, table",
            "table_rows": "tbody tr, table tr:not(:first-child)",
            "row_report_id": "td.col-report-id, td:nth-child(1)",
            "row_title": "td.col-title, td:nth-child(2)",
            "row_date": "td.col-date, td:nth-child(3)",
            "row_download_link": "td.col-download a, a[href*='/download/']",
        }
    },
    "labB": {
        "key": "labB",
        "name": "CityScan Imaging",
        "layout": "cards",
        "has_captcha": True,
        "login_path": "/labB/login",
        "reports_path": "/labB/reports",
        "download_path": "/labB/download/{filename}",
        "selectors": {
            # Login Form
            "username_input": "input#username, input[name='username'], input[type='text']",
            "password_input": "input#password, input[name='password'], input[type='password']",
            "submit_button": "button[type='submit'], button#login-btn, .login-button",
            "error_message": ".alert-error, .login-error, #error-message",
            "session_indicator": ".user-profile, #logout-btn, .reports-cards-container",

            # CAPTCHA Modal / Challenge
            "captcha_container": "#captcha-modal, .captcha-container, div[data-testid='captcha-modal']",
            "captcha_image": "#captcha-image, .captcha-box img, img[alt*='captcha']",
            "captcha_input": "input#captcha-input, input[name='captcha']",
            "captcha_submit": "button#verify-captcha, button.captcha-submit",

            # Cards Layout Selectors
            "cards_container": ".reports-cards-container, #cards-grid, .grid-cards",
            "card_item": ".report-card, div[data-testid='report-card']",
            "card_report_id": ".card-report-id, [data-field='report-id']",
            "card_title": ".card-title, h3, [data-field='title']",
            "card_date": ".card-date, [data-field='date']",
            "card_download_link": "a[href*='/download/'], button.download-btn",
        }
    },
    "labC": {
        "key": "labC",
        "name": "Vitals",
        "layout": "paginated",
        "has_captcha": True,
        "page_size": 3,
        "login_path": "/labC/login",
        "reports_path": "/labC/reports",
        "download_path": "/labC/download/{filename}",
        "selectors": {
            # Login Form
            "username_input": "input#username, input[name='username'], input[type='text']",
            "password_input": "input#password, input[name='password'], input[type='password']",
            "submit_button": "button[type='submit'], button#login-btn, .login-button",
            "error_message": ".alert-error, .login-error, #error-message",
            "session_indicator": ".user-profile, #logout-btn, .paginated-reports-list",

            # CAPTCHA Modal / Challenge
            "captcha_container": "#captcha-modal, .captcha-container, div[data-testid='captcha-modal']",
            "captcha_image": "#captcha-image, .captcha-box img, img[alt*='captcha']",
            "captcha_input": "input#captcha-input, input[name='captcha']",
            "captcha_submit": "button#verify-captcha, button.captcha-submit",

            # Paginated List Layout Selectors
            "list_container": ".paginated-reports-list, ul.reports-list, #reports-list",
            "list_item": "li.report-item, .report-row-item",
            "item_report_id": ".item-report-id, [data-field='report-id']",
            "item_title": ".item-title, .report-title, [data-field='title']",
            "item_date": ".item-date, .report-date, [data-field='date']",
            "item_download_link": "a[href*='/download/']",

            # Pagination Controls
            "pagination_container": ".pagination-nav, nav[aria-label='pagination']",
            "next_page_btn": "button#next-page, a.page-next, button[aria-label='Next page']:not([disabled])",
            "prev_page_btn": "button#prev-page, a.page-prev, button[aria-label='Previous page']",
            "current_page": ".page-current, span[aria-current='page']",
        }
    }
}
