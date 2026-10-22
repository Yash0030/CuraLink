"""Mock Lab Portals Server.

Implements the single Next.js-style site serving:
- Paths: /{lab}/login, /{lab}/reports, and /{lab}/download/{filename}
- labA (A1): Table layout, no CAPTCHA.
- labB (CityScan Imaging): Card layout, displays mock CAPTCHA modal.
- labC (Vitals): Paginated list layout (3 per page), displays mock CAPTCHA modal.
- Generates synthetic test PDFs for downloads on-demand.
"""

import io
import base64
from datetime import date
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.synthetic.generate_samples import (
    create_a1_report,
    create_cityscan_report,
    create_vitals_report,
    create_fake_html_pdf
)

mock_portal_app = FastAPI(title="Synthetic Lab Portals Mock Server")

# In-memory sessions
_LOGGED_IN_SESSIONS = set()

# Pre-generated synthetic report datasets for each lab
PORTAL_DATA = {
    "labA": [
        {"report_id": "A-20260121-001-2", "title": "Complete Blood Count (CBC)", "date": "2026-01-21", "filename": "A-20260121-001-2.pdf"},
        {"report_id": "A-20260115-002-1", "title": "Liver Function Test (LFT)", "date": "2026-01-15", "filename": "A-20260115-002-1.pdf"},
        {"report_id": "A-20251210-099-0", "title": "Thyroid Profile (T3, T4, TSH)", "date": "2025-12-10", "filename": "A-20251210-099-0.pdf"}, # out of typical range
    ],
    "labB": [
        {"report_id": "B-20260122-004-1", "title": "Chest X-Ray PA View", "date": "2026-01-22", "filename": "B-20260122-004-1.pdf"},
        {"report_id": "B-20260118-005-2", "title": "Ultrasound Whole Abdomen", "date": "2026-01-18", "filename": "B-20260118-005-2.pdf"},
        {"report_id": "B-20260128-007-3", "title": "MRI Lumbar Spine", "date": "2026-01-28", "filename": "B-20260128-007-3.pdf"},
    ],
    "labC": [
        {"report_id": "C-20260124-008-3", "title": "Comprehensive Lipid Panel", "date": "2026-01-24", "filename": "C-20260124-008-3.pdf"},
        {"report_id": "C-20260120-009-1", "title": "HbA1c Glycated Hemoglobin", "date": "2026-01-20", "filename": "C-20260120-009-1.pdf"},
        {"report_id": "C-20260117-010-2", "title": "Kidney Function Profile", "date": "2026-01-17", "filename": "C-20260117-010-2.pdf"},
        # Page 2 items
        {"report_id": "C-20260112-011-1", "title": "Vitamin D & B12 Panel", "date": "2026-01-12", "filename": "C-20260112-011-1.pdf"},
        {"report_id": "C-20260105-012-4", "title": "Urine Routine & Microscopic", "date": "2026-01-05", "filename": "C-20260105-012-4.pdf"},
        {"report_id": "C-20251120-088-2", "title": "Serum Electrolytes", "date": "2025-11-20", "filename": "C-20251120-088-2.pdf"},
    ]
}

def get_simple_captcha_svg() -> str:
    """Generates an inline SVG representing mock CAPTCHA text '4892'."""
    return """
    <svg xmlns="http://www.w3.org/2000/svg" width="160" height="60" viewBox="0 0 160 60" style="background:#e2e8f0;border-radius:4px;">
        <line x1="10" y1="15" x2="150" y2="45" stroke="#94a3b8" stroke-width="2"/>
        <line x1="20" y1="50" x2="140" y2="10" stroke="#cbd5e1" stroke-width="1.5"/>
        <text x="25" y="42" font-family="Courier, monospace" font-size="32" font-weight="bold" fill="#1e293b" letter-spacing="8">4892</text>
    </svg>
    """

# 1. Login Routes
@mock_portal_app.get("/{lab}/login", response_class=HTMLResponse)
async def login_page(lab: str):
    lab_names = {"labA": "A1 Reference Labs", "labB": "CityScan Imaging", "labC": "Vitals Diagnostic"}
    lab_name = lab_names.get(lab, lab)
    has_captcha = lab in ("labB", "labC")

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{lab_name} - Patient Portal Login</title>
        <style>
            body {{ font-family: system-ui, sans-serif; background: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
            .card {{ background: white; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 32px; width: 380px; }}
            h2 {{ margin-top: 0; color: #0f172a; font-size: 20px; }}
            .form-group {{ margin-bottom: 16px; }}
            label {{ display: block; margin-bottom: 6px; font-size: 13px; font-weight: 500; color: #475569; }}
            input[type='text'], input[type='password'] {{ width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }}
            button {{ width: 100%; padding: 10px; background: #2563eb; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }}
            button:hover {{ background: #1d4ed8; }}
            #captcha-modal {{ display: none; margin-top: 16px; padding: 16px; background: #f1f5f9; border-radius: 6px; }}
            .captcha-box {{ text-align: center; margin-bottom: 12px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>{lab_name}</h2>
            <p style="font-size: 13px; color: #64748b;">Sign in to view your diagnostic reports</p>
            <form id="login-form" onsubmit="handleLoginSubmit(event)" autocomplete="off">
                <div class="form-group">
                    <label for="username">Patient ID / Username</label>
                    <input type="text" id="username" name="username" placeholder="Username" required autocomplete="off" />
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Password" required autocomplete="new-password" />
                </div>
                <button type="submit" id="login-btn">Log In</button>

                <div id="captcha-modal">
                    <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #334155;">Security Verification</p>
                    <div class="captcha-box" id="captcha-image">
                        {get_simple_captcha_svg()}
                    </div>
                    <div class="form-group">
                        <input type="text" id="captcha-input" name="captcha" placeholder="Enter the 4 digits" />
                    </div>
                    <button type="button" id="verify-captcha" onclick="verifyCaptcha()">Verify & Access Reports</button>
                </div>
            </form>
        </div>
        <script>
            const hasCaptcha = {str(has_captcha).lower()};
            function handleLoginSubmit(e) {{
                e.preventDefault();
                const u = document.getElementById('username').value;
                const p = document.getElementById('password').value;
                if (!u || !p) return;

                if (hasCaptcha) {{
                    document.getElementById('captcha-modal').style.display = 'block';
                    document.getElementById('login-btn').style.display = 'none';
                }} else {{
                    document.cookie = "session_{lab}=valid; path=/";
                    window.location.href = "/{lab}/reports";
                }}
            }}
            function verifyCaptcha() {{
                const ans = document.getElementById('captcha-input').value.trim();
                if (ans === '4892' || ans.length > 0) {{
                    document.cookie = "session_{lab}=valid; path=/";
                    window.location.href = "/{lab}/reports";
                }} else {{
                    alert("Incorrect CAPTCHA");
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# 2. Reports Routes (Table, Cards, Paginated)
@mock_portal_app.get("/{lab}/reports", response_class=HTMLResponse)
async def reports_page(lab: str, request: Request, page: int = 1):
    cookie_name = f"session_{lab}"
    # Verify session cookie
    if request.cookies.get(cookie_name) != "valid":
        return Response(status_code=302, headers={"Location": f"/{lab}/login"})

    items = PORTAL_DATA.get(lab, [])
    lab_names = {"labA": "A1 Reference Labs", "labB": "CityScan Imaging", "labC": "Vitals Diagnostic"}
    lab_name = lab_names.get(lab, lab)

    common_header = f"""
    <div style="background: white; border-bottom: 1px solid #e2e8f0; padding: 16px 32px; display: flex; justify-content: space-between; align-items: center;">
        <h1 style="margin: 0; font-size: 20px; color: #0f172a;">{lab_name}</h1>
        <div class="user-profile" style="font-size: 14px; color: #64748b;">
            Logged in as <b>pt001</b> | <a href="/{lab}/login" id="logout-btn" style="color: #ef4444; text-decoration: none;">Logout</a>
        </div>
    </div>
    """

    if lab == "labA":
        # Table Layout
        rows_html = ""
        for item in items:
            rows_html += f"""
            <tr>
                <td class="col-report-id" style="padding: 12px; border-bottom: 1px solid #e2e8f0;">{item['report_id']}</td>
                <td class="col-title" style="padding: 12px; border-bottom: 1px solid #e2e8f0; font-weight: 500;">{item['title']}</td>
                <td class="col-date" style="padding: 12px; border-bottom: 1px solid #e2e8f0; color: #64748b;">{item['date']}</td>
                <td class="col-download" style="padding: 12px; border-bottom: 1px solid #e2e8f0;">
                    <a href="/labA/download/{item['filename']}" style="color: #2563eb; text-decoration: none; font-weight: 500;">Download PDF</a>
                </td>
            </tr>
            """
        body = f"""
        <div style="max-width: 900px; margin: 32px auto; background: white; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px;">
            <h2 style="margin-top: 0;">Diagnostic Lab Reports</h2>
            <table id="reports-table" class="reports-table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
                <thead>
                    <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
                        <th style="padding: 12px;">Report ID</th>
                        <th style="padding: 12px;">Test Name</th>
                        <th style="padding: 12px;">Date</th>
                        <th style="padding: 12px;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """

    elif lab == "labB":
        # Cards Layout
        cards_html = ""
        for item in items:
            cards_html += f"""
            <div class="report-card" data-testid="report-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="font-size: 12px; font-weight: 600; color: #0d9488; text-transform: uppercase;">Medical Imaging</div>
                <h3 class="card-title" data-field="title" style="margin: 8px 0; font-size: 16px; color: #0f172a;">{item['title']}</h3>
                <div class="card-report-id" data-field="report-id" style="font-size: 13px; color: #64748b; margin-bottom: 6px;">ID: {item['report_id']}</div>
                <div class="card-date" data-field="date" style="font-size: 13px; color: #64748b; margin-bottom: 16px;">Date: {item['date']}</div>
                <a href="/labB/download/{item['filename']}" class="download-btn" style="display: inline-block; padding: 8px 16px; background: #0d9488; color: white; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 500;">Download Report</a>
            </div>
            """
        body = f"""
        <div style="max-width: 900px; margin: 32px auto;">
            <h2 style="margin-top: 0;">Imaging Studies & Scans</h2>
            <div class="reports-cards-container" id="cards-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px;">
                {cards_html}
            </div>
        </div>
        """

    elif lab == "labC":
        # Paginated List Layout (3 per page)
        page_size = 3
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = items[start_idx:end_idx]
        has_next = end_idx < len(items)
        has_prev = page > 1

        list_html = ""
        for item in page_items:
            list_html += f"""
            <li class="report-item" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e2e8f0;">
                <div>
                    <div class="item-title" data-field="title" style="font-weight: 600; font-size: 15px; color: #1e1b4b;">{item['title']}</div>
                    <div style="font-size: 13px; color: #64748b; margin-top: 4px;">
                        <span class="item-report-id" data-field="report-id">Ref: {item['report_id']}</span> | 
                        <span class="item-date" data-field="date">Date: {item['date']}</span>
                    </div>
                </div>
                <div>
                    <a href="/labC/download/{item['filename']}" style="padding: 8px 16px; background: #7e22ce; color: white; text-decoration: none; border-radius: 6px; font-size: 13px;">View PDF</a>
                </div>
            </li>
            """

        prev_btn = f'<a href="/labC/reports?page={page-1}" class="page-prev" style="padding: 8px 16px; background: #e2e8f0; color: #334155; text-decoration: none; border-radius: 6px; font-size: 13px;">Previous</a>' if has_prev else '<button class="page-prev" disabled style="padding: 8px 16px; background: #f1f5f9; color: #94a3b8; border: none; border-radius: 6px; font-size: 13px;">Previous</button>'
        next_btn = f'<a href="/labC/reports?page={page+1}" id="next-page" class="page-next" style="padding: 8px 16px; background: #7e22ce; color: white; text-decoration: none; border-radius: 6px; font-size: 13px;">Next</a>' if has_next else '<button id="next-page" disabled style="padding: 8px 16px; background: #f1f5f9; color: #94a3b8; border: none; border-radius: 6px; font-size: 13px;">Next</button>'

        body = f"""
        <div style="max-width: 900px; margin: 32px auto; background: white; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px;">
            <h2 style="margin-top: 0;">Laboratory Panels</h2>
            <ul class="paginated-reports-list" style="list-style: none; padding: 0; margin: 0; border: 1px solid #e2e8f0; border-radius: 8px;">
                {list_html}
            </ul>
            <div class="pagination-nav" style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px;">
                {prev_btn}
                <span class="page-current" aria-current="page" style="font-size: 14px; color: #64748b;">Page {page} of {(len(items) + page_size - 1) // page_size}</span>
                {next_btn}
            </div>
        </div>
        """

    full_page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{lab_name} - Reports</title>
        <style>body {{ font-family: system-ui, sans-serif; background: #f8fafc; margin: 0; color: #0f172a; }}</style>
    </head>
    <body>
        {common_header}
        {body}
    </body>
    </html>
    """
    return HTMLResponse(content=full_page)

# 3. Download Route
@mock_portal_app.get("/{lab}/download/{filename}")
async def download_report_file(lab: str, filename: str, request: Request):
    cookie_name = f"session_{lab}"
    # Verify session
    if request.cookies.get(cookie_name) != "valid":
        return Response(status_code=302, headers={"Location": f"/{lab}/login"})

    # Dynamic generation based on lab
    if lab == "labA":
        pdf_bytes = create_a1_report(report_id=filename.replace(".pdf", ""))
    elif lab == "labB":
        pdf_bytes = create_cityscan_report(report_id=filename.replace(".pdf", ""))
    elif lab == "labC":
        pdf_bytes = create_vitals_report(report_id=filename.replace(".pdf", ""))
    else:
        pdf_bytes = create_a1_report()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )
