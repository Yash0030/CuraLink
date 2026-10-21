"""Unit tests for portal listing HTML parsers across table, cards, and paginated layouts."""

import pytest
from datetime import date
from bs4 import BeautifulSoup

def test_parse_a1_table_layout():
    html = """
    <table id="reports-table">
        <tbody>
            <tr>
                <td class="col-report-id">A-20260121-001-2</td>
                <td class="col-title">Complete Blood Count (CBC)</td>
                <td class="col-date">2026-01-21</td>
                <td class="col-download"><a href="/labA/download/A-20260121-001-2.pdf">Download</a></td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("#reports-table tbody tr")
    assert len(rows) == 1

    rep_id = rows[0].select_one(".col-report-id").get_text(strip=True)
    title = rows[0].select_one(".col-title").get_text(strip=True)
    date_str = rows[0].select_one(".col-date").get_text(strip=True)
    href = rows[0].select_one(".col-download a")["href"]

    assert rep_id == "A-20260121-001-2"
    assert title == "Complete Blood Count (CBC)"
    assert date_str == "2026-01-21"
    assert href.endswith(".pdf")

def test_parse_cityscan_cards_layout():
    html = """
    <div class="reports-cards-container">
        <div class="report-card">
            <h3 class="card-title">Chest X-Ray PA View</h3>
            <div class="card-report-id">ID: B-20260122-004-1</div>
            <div class="card-date">Date: 2026-01-22</div>
            <a class="download-btn" href="/labB/download/B-20260122-004-1.pdf">Download</a>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".reports-cards-container .report-card")
    assert len(cards) == 1

    title = cards[0].select_one(".card-title").get_text(strip=True)
    raw_id = cards[0].select_one(".card-report-id").get_text(strip=True)
    clean_id = raw_id.replace("ID:", "").strip()
    href = cards[0].select_one("a.download-btn")["href"]

    assert title == "Chest X-Ray PA View"
    assert clean_id == "B-20260122-004-1"
    assert href.endswith(".pdf")

def test_parse_vitals_paginated_layout():
    html = """
    <ul class="paginated-reports-list">
        <li class="report-item">
            <div class="item-title">Comprehensive Lipid Panel</div>
            <span class="item-report-id">Ref: C-20260124-008-3</span>
            <span class="item-date">Date: 2026-01-24</span>
            <a href="/labC/download/C-20260124-008-3.pdf">View PDF</a>
        </li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".paginated-reports-list li.report-item")
    assert len(items) == 1

    title = items[0].select_one(".item-title").get_text(strip=True)
    rep_id = items[0].select_one(".item-report-id").get_text(strip=True).replace("Ref:", "").strip()
    href = items[0].select_one("a")["href"]

    assert title == "Comprehensive Lipid Panel"
    assert rep_id == "C-20260124-008-3"
    assert href.endswith(".pdf")
