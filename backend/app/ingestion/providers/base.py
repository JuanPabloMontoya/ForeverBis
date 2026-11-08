"""Provider-independent protocol used by the catalog importer."""

from collections.abc import Iterator
from typing import Protocol

from backend.app.ingestion.providers.schemas import ItemListRecord, ItemResponse


class ItemProvider(Protocol):
    name: str
    base_url: str
    terms_url: str
    attribution_text: str
    current_build: str | None

    def iter_item_summaries(
        self, limit: int, *, per_page: int = 100
    ) -> Iterator[ItemListRecord]: ...

    def get_item_detail(self, item_id: int) -> ItemResponse: ...
