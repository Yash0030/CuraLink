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
            "username_input": "input#login-username, input[data-testid='login-username'], input#username, input[name='username'], input[type='text']",
            "password_input": "input#login-password, input[data-testid='login-password'], input#password, input[name='password'], input[type='password']",
            "submit_button": "button#login-submit, button[data-testid='login-submit'], button[type='submit'], button#login-btn",
            "error_message": ".alert-error, .login-error, #error-message, .error",
            "session_indicator": "table, #logout-link, button[data-testid='logout-link'], .user-profile",

            # Table Layout Selectors
            "table_container": "table#reports-table, table.reports-table, table",
            "table_rows": "tbody tr, table tr:not(:first-child)",
            "row_report_id": "td.col-report-id, td:nth-child(1)",
            "row_title": "td.col-title, td:nth-child(2)",
            "row_date": "td.col-date, td:nth-child(3)",
            "row_download_link": "a[data-testid='download-link'], td.col-download a, td:nth-child(4) a, a[href*='/download/']",

            # Fallback CAPTCHA Selectors (in case labA adds a challenge in the future)
            "captcha_container": "form[action*='captcha'], .panel, #captcha-modal, .captcha-container, div[data-testid='captcha-modal']",
            "captcha_image": "img[data-testid='captcha-image'], img[src*='captcha'], #captcha-image, .captcha-box img",
            "captcha_input": "input#captcha-input, input[data-testid='captcha-input'], input[name='answer'], input[name='captcha']",
            "captcha_submit": "button#captcha-submit, button[data-testid='captcha-submit'], button[type='submit'], button#verify-captcha",
        }
    },
    "labB": {
        "key": "labB",
        "name": "CityScan Imaging",
        "layout": "cards",
        "has_captcha": True,
        "login_path": "/labB/login",
        "captcha_path": "/labB/captcha",
        "reports_path": "/labB/reports",
        "download_path": "/labB/download/{filename}",
        "selectors": {
            # Login Form
            "username_input": "input#login-username, input[data-testid='login-username'], input#username, input[name='username'], input[type='text']",
            "password_input": "input#login-password, input[data-testid='login-password'], input#password, input[name='password'], input[type='password']",
            "submit_button": "button#login-submit, button[data-testid='login-submit'], button[type='submit'], button#login-btn",
            "error_message": ".alert-error, .login-error, #error-message, .error",
            "session_indicator": ".report-grid, #logout-link, button[data-testid='logout-link'], .reports-cards-container",

            # CAPTCHA Modal / Page Challenge
            "captcha_container": "form[action*='captcha'], .panel, #captcha-modal, .captcha-container, div[data-testid='captcha-modal']",
            "captcha_image": "img[data-testid='captcha-image'], img[src*='captcha'], #captcha-image, .captcha-box img",
            "captcha_input": "input#captcha-input, input[data-testid='captcha-input'], input[name='answer'], input[name='captcha']",
            "captcha_submit": "button#captcha-submit, button[data-testid='captcha-submit'], button[type='submit'], button#verify-captcha",

            # Cards Layout Selectors
            "cards_container": ".report-grid, .reports-cards-container, #cards-grid, .grid-cards",
            "card_item": "article.report-card, div.report-card, [data-testid='report-card']",
            "card_report_id": "strong, .card-report-id, [data-field='report-id']",
            "card_title": "h3, .card-title, [data-field='title']",
            "card_date": "p:has-text('Date:'), .card-date, [data-field='date']",
            "card_download_link": "a[data-testid='download-link'], a[href*='/download/'], button.download-btn",
        }
    },
    "labC": {
        "key": "labC",
        "name": "Vitals",
        "layout": "paginated",
        "has_captcha": True,
        "page_size": 3,
        "login_path": "/labC/login",
        "captcha_path": "/labC/captcha",
        "reports_path": "/labC/reports",
        "download_path": "/labC/download/{filename}",
        "selectors": {
            # Login Form
            "username_input": "input#login-username, input[data-testid='login-username'], input#username, input[name='username'], input[type='text']",
            "password_input": "input#login-password, input[data-testid='login-password'], input#password, input[name='password'], input[type='password']",
            "submit_button": "button#login-submit, button[data-testid='login-submit'], button[type='submit'], button#login-btn",
            "error_message": ".alert-error, .login-error, #error-message, .error",
            "session_indicator": "ul.report-list, #logout-link, button[data-testid='logout-link'], .paginated-reports-list",

            # CAPTCHA Modal / Page Challenge
            "captcha_container": "form[action*='captcha'], .panel, #captcha-modal, .captcha-container, div[data-testid='captcha-modal']",
            "captcha_image": "img[data-testid='captcha-image'], img[src*='captcha'], #captcha-image, .captcha-box img",
            "captcha_input": "input#captcha-input, input[data-testid='captcha-input'], input[name='answer'], input[name='captcha']",
            "captcha_submit": "button#captcha-submit, button[data-testid='captcha-submit'], button[type='submit'], button#verify-captcha",

            # Paginated List Layout Selectors
            "list_container": "ul.report-list, .paginated-reports-list, ul.reports-list, #reports-list",
            "list_item": "li[data-testid='report-row'], li.report-item, .report-row-item",
            "item_report_id": ".muted, .item-report-id, [data-field='report-id']",
            "item_title": "strong, .item-title, .report-title, [data-field='title']",
            "item_date": ".muted, .item-date, .report-date, [data-field='date']",
            "item_download_link": "a[data-testid='download-link'], a[href*='/download/']",

            # Pagination Controls
            "pagination_container": "nav.pager, .pagination-nav, nav[aria-label='pagination']",
            "next_page_btn": "a#next-page, a[data-testid='next-page'], button#next-page, a.page-next",
            "prev_page_btn": "a#previous-page, a[data-testid='previous-page'], button#prev-page, a.page-prev",
            "current_page": "nav.pager span, .page-current, span[aria-current='page']",
        }
    }
}
