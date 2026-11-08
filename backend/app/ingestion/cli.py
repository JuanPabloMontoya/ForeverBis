"""Safe command-line entry point for a bounded catalog import."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.ingestion.providers.thewowdb import TheWoWDBProvider
from backend.app.ingestion.services.item_importer import MAX_IMPORT_LIMIT, import_items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forever-bis-ingestion")
    commands = parser.add_subparsers(dest="command", required=True)
    import_parser = commands.add_parser("import-items", help="Import at most 100 Forever items")
    import_parser.add_argument("--limit", type=int, default=10)
    import_parser.add_argument("--per-page", type=int, default=100)
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate without writing (the default unless --write is supplied)",
    )
    import_parser.add_argument(
        "--write",
        action="store_true",
        help="Prompt for explicit confirmation before database writes",
    )
    import_parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Explicitly confirm database writes without an interactive prompt",
    )
    import_parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for the sanitized import/validation report JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > MAX_IMPORT_LIMIT:
        parser.error(f"--limit must be between 1 and {MAX_IMPORT_LIMIT}")
    if args.per_page < 1 or args.per_page > MAX_IMPORT_LIMIT:
        parser.error(f"--per-page must be between 1 and {MAX_IMPORT_LIMIT}")
    if args.dry_run and (args.write or args.confirm_write):
        parser.error("--dry-run cannot be combined with --write or --confirm-write")
    if args.write and args.confirm_write:
        parser.error("Use either --write or --confirm-write, not both")

    persist = args.write or args.confirm_write
    if args.write:
        try:
            confirmation = input(
                f"Import up to {args.limit} items from TheWoWDB into PostgreSQL? Type IMPORT: "
            )
        except EOFError:
            confirmation = ""
        if confirmation.strip() != "IMPORT":
            print("Import cancelled; no database writes were made.")
            return 1

    provider = TheWoWDBProvider()
    engine = None
    try:
        if persist:
            engine = create_database_engine(get_settings())
            session_factory = create_session_factory(engine)
            with session_factory() as session:
                report = import_items(
                    provider,
                    limit=args.limit,
                    per_page=args.per_page,
                    session=session,
                    dry_run=False,
                )
        else:
            report = import_items(
                provider,
                limit=args.limit,
                per_page=args.per_page,
                dry_run=True,
            )
    except Exception as exc:
        logging.getLogger(__name__).error("Catalog import failed: %s", exc)
        return 2
    finally:
        if engine is not None:
            engine.dispose()

    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["validated"] else 2


if __name__ == "__main__":
    sys.exit(main())
