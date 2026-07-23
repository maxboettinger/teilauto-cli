from __future__ import annotations

import json

import httpx

from teilauto.api.client import BASE_URL
from teilauto.api.errors import ApiError, NotFoundError
from teilauto.cli import cli


def test_bills_require_auth(runner, isolated_config):
    result = runner.invoke(cli, ["bills", "list"])
    assert result.exit_code != 0
    assert isinstance(result.exception, Exception)


def test_bills_list_table_with_total(runner, logged_in, respx_mock, bills_json):
    respx_mock.get(f"{BASE_URL}/bills").mock(return_value=httpx.Response(200, json=bills_json))
    result = runner.invoke(cli, ["bills", "list"])
    assert result.exit_code == 0, result.output
    assert "2026-07-001" in result.output
    assert "24.50 EUR" in result.output
    assert "46.40 EUR" in result.output  # 24.50 + 12.00 + 9.90 accumulated


def test_bills_list_year_filter(runner, logged_in, respx_mock, bills_json):
    respx_mock.get(f"{BASE_URL}/bills").mock(return_value=httpx.Response(200, json=bills_json))
    result = runner.invoke(cli, ["bills", "list", "--year", "2025", "--json"])
    assert result.exit_code == 0, result.output
    assert [b["id"] for b in json.loads(result.output)] == ["r-1"]


def test_bills_list_json_parses_both_sum_shapes(runner, logged_in, respx_mock, bills_json):
    respx_mock.get(f"{BASE_URL}/bills").mock(return_value=httpx.Response(200, json=bills_json))
    result = runner.invoke(cli, ["bills", "list", "--json"])
    assert result.exit_code == 0, result.output
    by_id = {b["id"]: b for b in json.loads(result.output)}
    assert by_id["r-3"]["gross_amount"] == 24.50  # sum.grossAmount
    assert by_id["r-2"]["gross_amount"] == 12.00  # sum.gross.amount
    assert by_id["r-2"]["currency"] == "EUR"


def test_bills_download_writes_pdf(runner, logged_in, respx_mock, bills_json, tmp_path):
    route = respx_mock.get(f"{BASE_URL}/bills").mock(
        return_value=httpx.Response(200, json=bills_json)
    )
    out = tmp_path / "bill.pdf"
    result = runner.invoke(cli, ["bills", "download", "r-2", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"%PDF-test"
    assert "expand=billDocument" in str(route.calls.last.request.url)


def test_bills_download_unknown_id_is_not_found(runner, logged_in, respx_mock, bills_json):
    respx_mock.get(f"{BASE_URL}/bills").mock(return_value=httpx.Response(200, json=bills_json))
    result = runner.invoke(cli, ["bills", "download", "nope"])
    assert result.exit_code != 0
    assert isinstance(result.exception, NotFoundError)


def test_bills_download_without_document_fails(runner, logged_in, respx_mock, bills_json):
    respx_mock.get(f"{BASE_URL}/bills").mock(return_value=httpx.Response(200, json=bills_json))
    result = runner.invoke(cli, ["bills", "download", "r-3"])
    assert result.exit_code != 0
    assert isinstance(result.exception, ApiError)


def test_bills_download_follows_reference_url(runner, logged_in, respx_mock, bills_json, tmp_path):
    with_ref = [dict(b) for b in bills_json]
    with_ref[1]["billDocument"] = {
        "reference": "https://docs.example/bill.pdf",
        "base64String": None,
        "mimeType": "application/pdf",
        "fileName": "rechnung-2026-06.pdf",
    }
    respx_mock.get(f"{BASE_URL}/bills").mock(return_value=httpx.Response(200, json=with_ref))
    respx_mock.get("https://docs.example/bill.pdf").mock(
        return_value=httpx.Response(200, content=b"%PDF-ref")
    )
    out = tmp_path / "bill.pdf"
    result = runner.invoke(cli, ["bills", "download", "r-2", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"%PDF-ref"
