from __future__ import annotations

import json

import httpx

from teilauto.api.client import API_KEY, BASE_URL
from teilauto.cli import cli


def test_providers_list_no_login_needed(runner, isolated_config, respx_mock, providers_json):
    route = respx_mock.get(f"{BASE_URL}/providers").mock(
        return_value=httpx.Response(200, json=providers_json)
    )
    result = runner.invoke(cli, ["providers", "list"])
    assert result.exit_code == 0, result.output
    assert "teilAuto Neckar-Alb" in result.output
    params = route.calls.last.request.url.params
    assert params["action"] == "CUSTOMER_LOGIN"
    assert params["expand"] == "remark"


def test_providers_list_marks_configured_provider(
    runner, isolated_config, respx_mock, providers_json
):
    respx_mock.get(f"{BASE_URL}/providers").mock(
        return_value=httpx.Response(200, json=providers_json)
    )
    result = runner.invoke(cli, ["providers", "list"])
    assert result.exit_code == 0, result.output
    marked = [line for line in result.output.splitlines() if "✓" in line]
    assert len(marked) == 1
    assert "118" in marked[0]  # the default api.prov_id


def test_providers_list_json(runner, isolated_config, respx_mock, providers_json):
    respx_mock.get(f"{BASE_URL}/providers").mock(
        return_value=httpx.Response(200, json=providers_json)
    )
    result = runner.invoke(cli, ["providers", "list", "--json"])
    assert result.exit_code == 0, result.output
    ids = [p["id"] for p in json.loads(result.output)]
    assert ids == ["1", "19", "118"]


def test_providers_list_uses_default_umbrella_key(
    runner, isolated_config, respx_mock, providers_json
):
    route = respx_mock.get(f"{BASE_URL}/providers").mock(
        return_value=httpx.Response(200, json=providers_json)
    )
    result = runner.invoke(cli, ["providers", "list"])
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.headers["x-api-key"] == API_KEY


def test_providers_list_honors_api_key_config(
    runner, isolated_config, respx_mock, providers_json, monkeypatch
):
    monkeypatch.setenv("TEILAUTO_API_KEY", "custom-key-123")
    route = respx_mock.get(f"{BASE_URL}/providers").mock(
        return_value=httpx.Response(200, json=providers_json)
    )
    result = runner.invoke(cli, ["providers", "list"])
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.headers["x-api-key"] == "custom-key-123"


def test_providers_list_empty(runner, isolated_config, respx_mock):
    respx_mock.get(f"{BASE_URL}/providers").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(cli, ["providers", "list"])
    assert result.exit_code == 0, result.output
    assert "No login-eligible operators" in result.output
