#!/usr/bin/env python3
"""Fetch a deliberately small, sanitized sample from TheWoWDB Forever API.

This script uses only the documented unauthenticated item list and item detail
endpoints. It has a hard item cap so it cannot be used for a full-dataset dump.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://thewowdb.com/api/v1"
API_HOST = "thewowdb.com"
USER_AGENT = "ForeverBIS-Phase1-Research/0.1"
MAX_ITEMS_HARD_LIMIT = 10
MAX_RETRY_AFTER_SECONDS = 60
ALLOWED_ITEM_FIELDS = (
    "id",
    "kind",
    "version",
    "version_label",
    "build",
    "name",
    "quality",
    "item_level",
    "required_level",
    "item_type",
    "item_subtype",
    "slot",
    "armor",
    "weapon",
    "stats",
    "effects",
    "classes",
    "icon_url",
    "links",
    "attribution",
)


class APIError(RuntimeError):
    """An API/network error with a user-readable message."""


class NotModified(Exception):
    """Raised when an ETag cache entry yields HTTP 304."""


def _retry_after_seconds(value: str | None) -> int:
    if not value:
        return 1
    try:
        return max(0, min(int(value), MAX_RETRY_AFTER_SECONDS))
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            seconds = int((when - datetime.now(UTC)).total_seconds())
            return max(0, min(seconds, MAX_RETRY_AFTER_SECONDS))
        except (TypeError, ValueError, OverflowError):
            return 1


def _safe_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    # Item effects may contain HTML intended for a tooltip. Keep plain text only.
    text = re.sub(r"<[^>]*>", " ", value)
    text = unescape(text)
    return " ".join(text.split())[:500]


def _sanitize_value(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return None
    if isinstance(value, dict):
        return {
            str(key): _sanitize_value(child, depth + 1)
            for key, child in list(value.items())[:30]
            if isinstance(key, str)
        }
    if isinstance(value, list):
        return [_sanitize_value(child, depth + 1) for child in value[:20]]
    return _safe_text(value)


def sanitize_item(item: dict[str, Any]) -> dict[str, Any]:
    """Retain only item fields needed for schema inspection; exclude AH prices."""
    return {key: _sanitize_value(item[key]) for key in ALLOWED_ITEM_FIELDS if key in item}


def validate_list_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise APIError("List result is not an object")
    item_id = value.get("id")
    name = value.get("name")
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
        raise APIError("List result has an invalid or missing item id")
    if not isinstance(name, str) or not name.strip():
        raise APIError(f"List result {item_id} has an invalid or missing name")
    if value.get("kind") not in (None, "item"):
        raise APIError(f"List result {item_id} is not an item")
    if value.get("version") not in (None, "forever"):
        raise APIError(f"List result {item_id} is not from Forever")
    return value


def parse_list_page(payload: Any) -> tuple[list[dict[str, Any]], bool]:
    if not isinstance(payload, dict):
        raise APIError("List response must be a JSON object")
    if payload.get("version") not in (None, "forever"):
        raise APIError("Response version is not forever")
    if payload.get("kind") not in (None, "item"):
        raise APIError("Response kind is not item")
    records = payload.get("results")
    if not isinstance(records, list):
        raise APIError("List response is missing a results array")
    if not isinstance(payload.get("has_more"), bool):
        raise APIError("List response is missing the documented has_more flag")
    return [validate_list_record(record) for record in records], payload["has_more"]


class WowDBClient:
    def __init__(
        self,
        *,
        api_root: str = API_ROOT,
        timeout: float = 15,
        opener: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
        etag_cache_path: Path | None = None,
    ) -> None:
        self.api_root = api_root.rstrip("/")
        self.timeout = timeout
        self.opener = opener
        self.sleep = sleep
        self.etag_cache_path = etag_cache_path
        self.etags = self._load_etags(etag_cache_path)

    @staticmethod
    def _load_etags(path: Path | None) -> dict[str, str]:
        if path is None or not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_etags(self) -> None:
        if self.etag_cache_path is not None:
            self.etag_cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.etag_cache_path.write_text(
                json.dumps(self.etags, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    def get_json(self, url: str) -> Any:
        if not url.startswith(self.api_root + "/"):
            raise APIError("Refusing to request a URL outside the configured API root")
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        if url in self.etags:
            headers["If-None-Match"] = self.etags[url]
        request = Request(url, headers=headers, method="GET")

        for attempt in range(2):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    body = response.read()
                    status = getattr(response, "status", 200)
                    etag = response.headers.get("ETag")
                    if etag:
                        self.etags[url] = etag
                        self._save_etags()
                    if status == 304:
                        raise NotModified(url)
                    try:
                        return json.loads(body.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise APIError(f"Invalid JSON from {url}: {exc}") from exc
            except HTTPError as exc:
                if exc.code == 304:
                    raise NotModified(url) from exc
                if exc.code == 429 and attempt == 0:
                    delay = _retry_after_seconds(exc.headers.get("Retry-After"))
                    self.sleep(delay)
                    continue
                retry = exc.headers.get("Retry-After") if exc.code == 429 else None
                suffix = f"; Retry-After={retry}" if retry else ""
                raise APIError(f"HTTP {exc.code} requesting {url}{suffix}") from exc
            except URLError as exc:
                raise APIError(f"Network error requesting {url}: {exc.reason}") from exc
        raise APIError(f"HTTP 429 persisted after one retry requesting {url}")

    def list_page(self, page: int, per_page: int) -> Any:
        query = urlencode({"page": page, "per_page": per_page})
        return self.get_json(f"{self.api_root}/forever/item/?{query}")

    def item_detail(self, item_id: int) -> Any:
        return self.get_json(f"{self.api_root}/forever/item/{item_id}")


def fetch_sample(
    client: WowDBClient, *, max_items: int = 3, per_page: int = 3
) -> tuple[list[dict[str, Any]], str | None]:
    if not 1 <= max_items <= MAX_ITEMS_HARD_LIMIT:
        raise ValueError(f"max_items must be between 1 and {MAX_ITEMS_HARD_LIMIT}")
    if not 1 <= per_page <= MAX_ITEMS_HARD_LIMIT:
        raise ValueError(f"per_page must be between 1 and {MAX_ITEMS_HARD_LIMIT}")

    sampled: list[dict[str, Any]] = []
    builds: list[str] = []
    page = 1
    while len(sampled) < max_items:
        payload = client.list_page(page, min(per_page, max_items - len(sampled)))
        records, has_more = parse_list_page(payload)
        build = payload.get("build") if isinstance(payload, dict) else None
        if isinstance(build, str) and build not in builds:
            builds.append(build)
        if not records:
            break

        for record in records:
            if len(sampled) >= max_items:
                break
            detail = client.item_detail(record["id"])
            if not isinstance(detail, dict):
                raise APIError(f"Item detail {record['id']} is not a JSON object")
            if detail.get("id") != record["id"]:
                raise APIError(f"Item detail id mismatch for {record['id']}")
            if detail.get("version") not in (None, "forever"):
                raise APIError(f"Item detail {record['id']} is not from Forever")
            detail_build = detail.get("build")
            if isinstance(detail_build, str) and detail_build not in builds:
                builds.append(detail_build)
            sampled.append(sanitize_item(detail))

        if not has_more:
            break
        page += 1
    return sampled, ", ".join(builds) or None


def write_sample(path: Path, items: list[dict[str, Any]], build: str | None) -> None:
    output = {
        "source": "TheWoWDB Forever public API",
        "source_url": "https://thewowdb.com/developers/",
        "attribution": "Data from TheWoWDB (thewowdb.com)",
        "attribution_required": True,
        "terms_url": "https://thewowdb.com/developers/#terms",
        "sampled_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "builds": build,
        "sample_count": len(items),
        "sanitization": (
            "Allowlisted item fields only; market prices, faction price scans, tooltip HTML, "
            "and unrelated response fields omitted."
        ),
        "items": items,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/data-source-sample.json"))
    parser.add_argument(
        "--max-items", type=int, default=3, help="1-10 only; never fetches the full dataset"
    )
    parser.add_argument(
        "--per-page", type=int, default=3, help="1-10; uses documented page/per_page pagination"
    )
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--etag-cache", type=Path, help="optional local URL-to-ETag cache file")
    args = parser.parse_args(argv)
    if not 1 <= args.max_items <= MAX_ITEMS_HARD_LIMIT:
        parser.error(f"--max-items must be between 1 and {MAX_ITEMS_HARD_LIMIT}")
    if not 1 <= args.per_page <= MAX_ITEMS_HARD_LIMIT:
        parser.error(f"--per-page must be between 1 and {MAX_ITEMS_HARD_LIMIT}")

    try:
        client = WowDBClient(timeout=args.timeout, etag_cache_path=args.etag_cache)
        items, build = fetch_sample(client, max_items=args.max_items, per_page=args.per_page)
        write_sample(args.output, items, build)
    except NotModified:
        print("API returned 304 Not Modified; no new sample written.", file=sys.stderr)
        return 0
    except (APIError, OSError, ValueError) as exc:
        print(f"TheWoWDB exploration failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Saved {len(items)} sanitized Forever item(s) to {args.output} "
        f"(build: {build or 'not returned'})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
