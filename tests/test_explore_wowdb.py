import io
import json
import unittest
from email.message import Message
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
from urllib.error import HTTPError

from scripts.explore_wowdb import (
    APIError,
    WowDBClient,
    fetch_sample,
    parse_list_page,
    sanitize_item,
    validate_list_record,
)


def response(payload, *, headers=None, status=200):
    class FakeResponse:
        def __init__(self):
            self.status = status
            self.headers = Message()
            for key, value in (headers or {}).items():
                self.headers[key] = value

        def read(self):
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    return FakeResponse()


class ParseTests(unittest.TestCase):
    def test_parses_documented_response_and_build(self):
        records, has_more = parse_list_page(
            {
                "version": "forever",
                "kind": "item",
                "build": "build-sample",
                "results": [{"id": 25, "name": "Worn Shortsword", "version": "forever"}],
                "has_more": True,
            }
        )
        self.assertEqual(records[0]["id"], 25)
        self.assertTrue(has_more)

    def test_optional_fields_may_be_missing(self):
        item = validate_list_record({"id": 7, "name": "Sample", "version": "forever"})
        self.assertNotIn("stats", item)

    def test_rejects_invalid_item_records(self):
        for item in (None, {}, {"id": "7", "name": "Sample"}, {"id": 7, "name": " "}):
            with self.subTest(item=item), self.assertRaises(APIError):
                validate_list_record(item)

    def test_rejects_invalid_envelope(self):
        with self.assertRaises(APIError):
            parse_list_page({"results": [], "has_more": "false"})

    def test_sanitizer_omits_prices_and_strips_html(self):
        clean = sanitize_item(
            {
                "id": 7,
                "name": "Sample",
                "price": {"market": 123},
                "faction_prices": [{"faction": "Alliance"}],
                "effects": ["<span>Use:</span> effect"],
            }
        )
        self.assertNotIn("price", clean)
        self.assertNotIn("faction_prices", clean)
        self.assertEqual(clean["effects"], ["Use: effect"])


class HTTPTests(unittest.TestCase):
    def test_http_error_is_reported(self):
        headers = Message()
        opener = Mock(
            side_effect=HTTPError("https://thewowdb.com/api", 500, "fail", headers, io.BytesIO())
        )
        client = WowDBClient(opener=opener, sleep=Mock())
        with self.assertRaisesRegex(APIError, "HTTP 500"):
            client.get_json("https://thewowdb.com/api/v1/forever/item/?page=1&per_page=1")

    def test_429_honors_retry_after_once(self):
        headers = Message()
        headers["Retry-After"] = "0"
        error = HTTPError("https://thewowdb.com/api", 429, "slow down", headers, io.BytesIO())
        opener = Mock(side_effect=[error, response({"ok": True})])
        sleep = Mock()
        client = WowDBClient(opener=opener, sleep=sleep)
        result = client.get_json("https://thewowdb.com/api/v1/forever/item/?page=1&per_page=1")
        self.assertEqual(result, {"ok": True})
        sleep.assert_called_once_with(0)

    def test_etag_is_sent_and_saved(self):
        with TemporaryDirectory() as temp_dir:
            etag_file = Path(temp_dir) / "etags.json"
            url = "https://thewowdb.com/api/v1/forever/item/?page=1&per_page=1"
            opener = Mock(return_value=response({"ok": True}, headers={"ETag": 'W/"abc"'}))
            client = WowDBClient(opener=opener, etag_cache_path=etag_file)
            client.get_json(url)
            self.assertEqual(json.loads(etag_file.read_text(encoding="utf-8"))[url], 'W/"abc"')

            second_opener = Mock(return_value=response({"ok": True}))
            second_client = WowDBClient(opener=second_opener, etag_cache_path=etag_file)
            second_client.get_json(url)
            request = second_opener.call_args.args[0]
            self.assertEqual(request.get_header("If-none-match"), 'W/"abc"')


class PaginationTests(unittest.TestCase):
    def test_fetches_next_page_until_requested_sample_size(self):
        client = Mock()
        client.list_page.side_effect = [
            {
                "version": "forever",
                "kind": "item",
                "build": "b1",
                "results": [{"id": 1, "name": "One"}],
                "has_more": True,
            },
            {
                "version": "forever",
                "kind": "item",
                "build": "b1",
                "results": [{"id": 2, "name": "Two"}],
                "has_more": False,
            },
        ]
        client.item_detail.side_effect = [
            {"id": 1, "name": "One", "version": "forever"},
            {"id": 2, "name": "Two", "version": "forever"},
        ]
        items, build = fetch_sample(client, max_items=2, per_page=1)
        self.assertEqual([item["id"] for item in items], [1, 2])
        self.assertEqual(build, "b1")
        self.assertEqual([call.args for call in client.list_page.call_args_list], [(1, 1), (2, 1)])

    def test_hard_cap_prevents_full_ingestion(self):
        with self.assertRaises(ValueError):
            fetch_sample(Mock(), max_items=11, per_page=10)


if __name__ == "__main__":
    unittest.main()
