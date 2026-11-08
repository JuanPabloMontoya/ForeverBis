"""Documented, bounded client for TheWoWDB's public Forever item API."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from pydantic import ValidationError

from backend.app.ingestion.providers.schemas import (
    ItemListRecord,
    ItemListResponse,
    ItemResponse,
    ItemTooltipResponse,
)

API_ROOT = "https://thewowdb.com/api/v1"
API_ORIGIN = "https://thewowdb.com"
MAX_PAGE_SIZE = 100
MAX_PAGES = 200
MAX_RETRY_AFTER_SECONDS = 60
REQUEST_INTERVAL_SECONDS = 0.51
MAX_RETRIES = 3
logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Safe provider error without request headers or credentials."""


@dataclass
class CachedResponse:
    payload: Any
    etag: str | None
    expires_at: float


def retry_after_seconds(value: str | None) -> float:
    if not value:
        return 1.0
    try:
        return max(0.0, min(float(value), MAX_RETRY_AFTER_SECONDS))
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            return max(
                0.0,
                min((when - datetime.now(UTC)).total_seconds(), MAX_RETRY_AFTER_SECONDS),
            )
        except (TypeError, ValueError, OverflowError):
            return 1.0


class TheWoWDBProvider:
    name = "TheWoWDB"
    base_url = "https://thewowdb.com/"
    api_root = API_ROOT
    terms_url = "https://thewowdb.com/developers/#terms"
    attribution_text = "Data from TheWoWDB (thewowdb.com)"

    def __init__(
        self,
        *,
        timeout: float = 15.0,
        opener: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.timeout = timeout
        self.opener = opener
        self.sleep = sleep
        self.monotonic = monotonic
        self._last_request_at: float | None = None
        self._cache: dict[str, CachedResponse] = {}
        self._raw_summaries: dict[int, dict[str, Any]] = {}
        self._endpoint_etags: dict[str, str | None] = {}
        self.current_build: str | None = None

    @staticmethod
    def _validate_api_url(url: str) -> None:
        parsed = urlparse(url)
        allowed = (
            parsed.path == "/api/v1/forever/item/"
            or bool(re.fullmatch(r"/api/v1/forever/item/\d+", parsed.path))
            or parsed.path == "/api/v1/forever/search/"
            or bool(re.fullmatch(r"/api/v1/tooltip/forever/item/\d+", parsed.path))
            or parsed.path == "/api/v1/forever/quest/"
            or bool(re.fullmatch(r"/api/v1/forever/quest/\d+", parsed.path))
            or parsed.path == "/api/v1/forever/npc/"
            or bool(re.fullmatch(r"/api/v1/forever/npc/\d+", parsed.path))
        )
        if parsed.scheme != "https" or parsed.netloc != "thewowdb.com" or not allowed:
            raise ProviderError("Refusing a non-documented or external provider URL")

    def _pace(self) -> None:
        now = self.monotonic()
        if self._last_request_at is not None:
            delay = REQUEST_INTERVAL_SECONDS - (now - self._last_request_at)
            if delay > 0:
                self.sleep(delay)
        self._last_request_at = self.monotonic()

    def get_json(
        self,
        url: str,
        *,
        revalidate: bool = False,
        etag: str | None = None,
        cached_payload: Any = None,
        cache_seconds: int = 3600,
    ) -> Any:
        self._validate_api_url(url)
        cached = self._cache.get(url)
        if cached and cached.expires_at > self.monotonic() and not revalidate:
            return cached.payload

        headers = {
            "Accept": "application/json",
            "User-Agent": "ForeverBIS/0.3 (+https://thewowdb.com/developers/)",
        }
        effective_etag = cached.etag if cached and cached.etag else etag
        if effective_etag:
            headers["If-None-Match"] = effective_etag
        request = Request(url, headers=headers, method="GET")

        for attempt in range(MAX_RETRIES + 1):
            self._pace()
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    status = getattr(response, "status", 200)
                    if status == 304:
                        payload = cached.payload if cached else cached_payload
                        if payload is None:
                            raise ProviderError("TheWoWDB returned 304 without a cached payload")
                        self._cache[url] = CachedResponse(
                            payload, effective_etag, self.monotonic() + cache_seconds
                        )
                        self._endpoint_etags[url] = effective_etag
                        return payload
                    body = response.read()
                    try:
                        payload = json.loads(body.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ProviderError("TheWoWDB returned invalid JSON") from exc
                    etag = response.headers.get("ETag")
                    self._cache[url] = CachedResponse(
                        payload=payload,
                        etag=etag,
                        expires_at=self.monotonic() + cache_seconds,
                    )
                    self._endpoint_etags[url] = etag
                    logger.info("Received provider response", extra={"provider": self.name})
                    return payload
            except HTTPError as exc:
                if exc.code == 304 and cached:
                    cached.expires_at = self.monotonic() + cache_seconds
                    self._endpoint_etags[url] = cached.etag
                    return cached.payload
                if exc.code == 304 and cached_payload is not None:
                    self._cache[url] = CachedResponse(
                        cached_payload, effective_etag, self.monotonic() + cache_seconds
                    )
                    self._endpoint_etags[url] = effective_etag
                    return cached_payload
                if exc.code == 429 and attempt < MAX_RETRIES:
                    self.sleep(retry_after_seconds(exc.headers.get("Retry-After")))
                    continue
                if exc.code in {500, 502, 503, 504} and attempt < MAX_RETRIES:
                    self.sleep(min(2**attempt, MAX_RETRY_AFTER_SECONDS))
                    continue
                suffix = (
                    f"; Retry-After={exc.headers.get('Retry-After')}" if exc.code == 429 else ""
                )
                raise ProviderError(f"TheWoWDB HTTP {exc.code}{suffix}") from exc
            except (URLError, TimeoutError, ConnectionError) as exc:
                if attempt < MAX_RETRIES:
                    self.sleep(min(2**attempt, MAX_RETRY_AFTER_SECONDS))
                    continue
                raise ProviderError("TheWoWDB network request failed") from exc
        raise ProviderError("TheWoWDB request exhausted retry attempts")

    def list_page(self, page: int, per_page: int, *, search: str | None = None) -> ItemListResponse:
        if not 1 <= page <= MAX_PAGES:
            raise ValueError(f"page must be between 1 and {MAX_PAGES}")
        if not 1 <= per_page <= MAX_PAGE_SIZE:
            raise ValueError(f"per_page must be between 1 and {MAX_PAGE_SIZE}")
        if search is not None and (not search.strip() or len(search) > 64):
            raise ValueError("search must contain 1 to 64 characters")
        params = {"page": page, "per_page": per_page}
        if search:
            params["q"] = search.strip()
        url = f"{self.api_root}/forever/item/?{urlencode(params)}"
        payload = self.get_json(url)
        try:
            response = ItemListResponse.model_validate(payload)
            self.current_build = response.build
            if isinstance(payload, dict):
                for raw in payload.get("results", []):
                    if isinstance(raw, dict) and isinstance(raw.get("id"), int):
                        self._raw_summaries[raw["id"]] = raw
            return response
        except ValidationError as exc:
            raise ProviderError("TheWoWDB item list did not match the expected schema") from exc

    def iter_item_summaries(
        self,
        limit: int,
        *,
        per_page: int = MAX_PAGE_SIZE,
        search: str | None = None,
        start_page: int = 1,
    ) -> Iterator[ItemListRecord]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if not 1 <= per_page <= MAX_PAGE_SIZE:
            raise ValueError(f"per_page must be between 1 and {MAX_PAGE_SIZE}")

        if not 1 <= start_page <= MAX_PAGES:
            raise ValueError(f"start_page must be between 1 and {MAX_PAGES}")
        seen: set[int] = set()
        page = start_page
        next_url: str | None = None
        while len(seen) < limit and page <= MAX_PAGES:
            response = self.list_page(page, per_page, search=search) if not next_url else None
            if next_url:
                payload = self.get_json(next_url)
                try:
                    response = ItemListResponse.model_validate(payload)
                    self.current_build = response.build
                    if isinstance(payload, dict):
                        for raw in payload.get("results", []):
                            if isinstance(raw, dict) and isinstance(raw.get("id"), int):
                                self._raw_summaries[raw["id"]] = raw
                except ValidationError as exc:
                    raise ProviderError(
                        "TheWoWDB item list did not match the expected schema"
                    ) from exc
            assert response is not None
            for record in response.results:
                if record.id in seen:
                    continue
                seen.add(record.id)
                yield record
                if len(seen) >= limit:
                    break
            if len(seen) >= limit or not response.has_more:
                return
            page += 1
            next_url = None
            if response.links and response.links.next:
                candidate = urljoin(API_ORIGIN, response.links.next)
                self._validate_api_url(candidate)
                params = parse_qs(urlparse(candidate).query)
                if "page" not in params or "per_page" not in params:
                    raise ProviderError("TheWoWDB next page link is missing pagination parameters")
                next_url = candidate
        if len(seen) < limit and page > MAX_PAGES:
            logger.warning("Provider page safety bound reached", extra={"page_limit": MAX_PAGES})

    def get_item_detail(
        self,
        item_id: int,
        *,
        etag: str | None = None,
        cached_payload: dict[str, Any] | None = None,
    ) -> ItemResponse:
        if item_id <= 0:
            raise ValueError("item_id must be positive")
        payload = self.get_json(
            f"{self.api_root}/forever/item/{item_id}",
            revalidate=etag is not None,
            etag=etag,
            cached_payload=cached_payload,
        )
        try:
            detail = ItemResponse.model_validate(payload)
        except ValidationError as exc:
            raise ProviderError(
                f"TheWoWDB item detail {item_id} did not match the expected schema"
            ) from exc
        if detail.id != item_id:
            raise ProviderError(f"TheWoWDB item detail ID mismatch for {item_id}")
        return detail

    def get_item_tooltip(self, item_id: int) -> ItemTooltipResponse:
        """Fetch documented tooltip fields; callers must not persist/render returned HTML."""
        if item_id <= 0:
            raise ValueError("item_id must be positive")
        url = f"{API_ORIGIN}/api/v1/tooltip/forever/item/{item_id}"
        payload = self.get_json(url, cache_seconds=300)
        try:
            return ItemTooltipResponse.model_validate(payload)
        except ValidationError as exc:
            raise ProviderError(
                "TheWoWDB item tooltip did not match its expected envelope"
            ) from exc

    def search_forever(self, query: str) -> dict[str, Any]:
        """Use documented cross-kind search for discovery only, not as a complete catalog."""
        if not query.strip() or len(query) > 64:
            raise ValueError("query must contain 1 to 64 characters")
        payload = self.get_json(f"{self.api_root}/forever/search/?{urlencode({'q': query})}")
        if not isinstance(payload, dict):
            raise ProviderError("TheWoWDB search response was not an object")
        return payload

    def get_raw_item_payload(self, item_id: int) -> dict[str, Any]:
        detail_url = f"{self.api_root}/forever/item/{item_id}"
        detail = self._cache.get(detail_url)
        return {
            "summary": self._raw_summaries.get(item_id),
            "detail": detail.payload if detail and isinstance(detail.payload, dict) else None,
        }

    def get_item_etag(self, item_id: int) -> str | None:
        return self._endpoint_etags.get(f"{self.api_root}/forever/item/{item_id}")
