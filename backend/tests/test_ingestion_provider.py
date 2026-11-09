"""Mocked HTTP contract tests for the documented TheWoWDB routes."""

import json
from email.message import Message
from urllib.error import HTTPError

import pytest

from backend.app.ingestion.providers.thewowdb import ProviderError, TheWoWDBProvider


class FakeResponse:
    def __init__(self, payload, *, status=200, headers=None):
        self.status = status
        self.headers = headers or Message()
        self.body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def list_page(records, *, page=1, per_page=2, has_more=False, next_url=None):
    return {
        "version": "forever",
        "kind": "item",
        "build": "mock-build",
        "page": page,
        "per_page": per_page,
        "count": len(records),
        "total": None,
        "has_more": has_more,
        "links": {"next": next_url},
        "results": records,
    }


def item_summary(item_id):
    return {
        "id": item_id,
        "kind": "item",
        "version": "forever",
        "name": f"Mock Item {item_id}",
        "quality": "common",
        "item_level": 1,
        "required_level": 1,
    }


def provider_for(responses, *, sleep=lambda _seconds: None):
    def opener(request, timeout):
        assert timeout == 5
        return responses.pop(0)

    return TheWoWDBProvider(timeout=5, opener=opener, sleep=sleep, monotonic=lambda: 0)


def test_list_response_parsing_and_forever_version_validation():
    provider = provider_for([FakeResponse(list_page([item_summary(7)]))])
    response = provider.list_page(1, 2)
    assert response.results[0].id == 7
    assert provider.current_build == "mock-build"

    invalid = list_page([item_summary(7)])
    invalid["version"] = "retail"
    provider = provider_for([FakeResponse(invalid)])
    with pytest.raises(ProviderError, match="expected schema"):
        provider.list_page(1, 2)


def test_missing_and_invalid_item_records_are_rejected():
    provider = provider_for([FakeResponse(list_page([{"name": "Missing ID"}]))])
    with pytest.raises(ProviderError, match="expected schema"):
        provider.list_page(1, 2)
    with pytest.raises(ValueError, match="positive"):
        provider.get_item_detail(0)


def test_pagination_follows_only_documented_item_routes_and_respects_limit():
    next_url = "https://thewowdb.com/api/v1/forever/item/?page=2&per_page=2"
    responses = [
        FakeResponse(
            list_page(
                [item_summary(1), item_summary(2)],
                has_more=True,
                next_url=next_url,
            )
        ),
        FakeResponse(list_page([item_summary(3), item_summary(4)], page=2)),
    ]
    requests = []

    def opener(request, timeout):
        requests.append(request.full_url)
        return responses.pop(0)

    provider = TheWoWDBProvider(opener=opener, sleep=lambda _seconds: None, monotonic=lambda: 0)
    ids = [record.id for record in provider.iter_item_summaries(3, per_page=2)]
    assert ids == [1, 2, 3]
    assert requests[1] == next_url

    with pytest.raises(ProviderError, match="external provider URL"):
        provider.get_json("https://example.com/api/v1/forever/item/?page=2")


def test_full_import_page_mode_does_not_retain_catalog_payloads_in_memory():
    provider = provider_for([FakeResponse(list_page([item_summary(91)]))])
    payload = provider.list_page_payload(
        1,
        2,
        use_memory_cache=False,
        retain_summaries=False,
    )
    assert payload["results"][0]["id"] == 91
    assert provider._cache == {}
    assert provider._raw_summaries == {}


def test_etag_revalidation_uses_cached_body_on_304():
    headers = Message()
    headers["ETag"] = 'W/"record-v1"'
    response_payload = {"version": "forever", "kind": "item", "results": []}
    requests = []

    def opener(request, timeout):
        requests.append(request)
        if len(requests) == 1:
            return FakeResponse(response_payload, headers=headers)
        assert request.get_header("If-none-match") == 'W/"record-v1"'
        error_headers = Message()
        raise HTTPError(request.full_url, 304, "Not Modified", error_headers, None)

    provider = TheWoWDBProvider(opener=opener, sleep=lambda _seconds: None, monotonic=lambda: 0)
    url = "https://thewowdb.com/api/v1/forever/item/?page=1&per_page=1"
    assert provider.get_json(url) == response_payload
    assert provider.get_json(url, revalidate=True) == response_payload
    assert len(requests) == 2


def test_rate_limit_retries_after_retry_after_header():
    delays = []
    first = True

    def opener(request, timeout):
        nonlocal first
        if first:
            first = False
            headers = Message()
            headers["Retry-After"] = "0"
            raise HTTPError(request.full_url, 429, "Too Many Requests", headers, None)
        return FakeResponse({"ok": True})

    provider = TheWoWDBProvider(opener=opener, sleep=delays.append, monotonic=lambda: 0)
    result = provider.get_json("https://thewowdb.com/api/v1/forever/item/5")
    assert result == {"ok": True}
    assert 0.0 in delays
    assert any(delay >= 0.5 for delay in delays)
    assert provider.get_item_status_counts(5) == {"429": 1, "200": 1}


def test_transient_http_failure_retries_and_terminal_failure_is_safe():
    attempts = 0

    def recovers(request, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise HTTPError(request.full_url, 503, "Unavailable", Message(), None)
        return FakeResponse({"ok": True})

    provider = TheWoWDBProvider(opener=recovers, sleep=lambda _seconds: None, monotonic=lambda: 0)
    assert provider.get_json("https://thewowdb.com/api/v1/forever/item/5") == {"ok": True}
    assert attempts == 2

    def unavailable(request, timeout):
        raise HTTPError(request.full_url, 404, "Not Found", Message(), None)

    provider = TheWoWDBProvider(
        opener=unavailable, sleep=lambda _seconds: None, monotonic=lambda: 0
    )
    with pytest.raises(ProviderError, match="HTTP 404"):
        provider.get_json("https://thewowdb.com/api/v1/forever/item/5")


def test_timeout_retries_are_bounded_and_documented_tooltip_is_parsed():
    attempts = 0

    def times_out(request, timeout):
        nonlocal attempts
        attempts += 1
        raise TimeoutError("timed out")

    provider = TheWoWDBProvider(
        opener=times_out,
        sleep=lambda _seconds: None,
        monotonic=lambda: 0,
    )
    with pytest.raises(ProviderError, match="network request failed"):
        provider.get_json("https://thewowdb.com/api/v1/forever/item/5")
    assert attempts == 4

    tooltip_payload = {
        "id": 5,
        "kind": "item",
        "version": "forever",
        "fields": {"stats": []},
        "html": "<div>untrusted display markup</div>",
    }
    provider = provider_for([FakeResponse(tooltip_payload)])
    tooltip = provider.get_item_tooltip(5)
    assert tooltip.fields == {"stats": []}
    assert tooltip.html == "<div>untrusted display markup</div>"
