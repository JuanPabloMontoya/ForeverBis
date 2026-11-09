"""CLI for safe, resumable full TheWoWDB Forever catalog imports."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.ingestion.providers.thewowdb import MAX_PAGE_SIZE, TheWoWDBProvider
from backend.app.ingestion.services.full_catalog_import import (
    create_catalog_job,
    enumerate_full_catalog,
    full_catalog_report,
    hydrate_full_catalog,
)
from backend.app.models.operations import FullCatalogImportJob


def _report_markdown(report: dict[str, Any]) -> str:
    enumeration = report["enumeration"]
    hydration = report["hydration"]
    catalog = report["local_catalog"]
    pages_discovered = enumeration["pages_discovered"] or "unknown"
    pages_remaining = (
        enumeration["pages_remaining"] if enumeration["pages_remaining"] is not None else "unknown"
    )
    item_changes = (
        f"{catalog['new_records']} / {catalog['updated_records']} / {catalog['unchanged_records']}"
    )
    return f"""# TheWoWDB Forever full catalog import

- Job: `{report["job_id"]}`
- Generated: {report["generated_at"]}
- Provider build: `{report["provider_build"] or "unknown"}`
- Overall status: **{report["status"]}**
- Enumeration: **{"complete" if enumeration["complete"] else "incomplete"}**
- Hydration: **{"complete" if hydration["complete"] else "partial"}**

## Enumeration

| Measure | Count |
|---|---:|
| Pages completed / discovered | {enumeration["pages_completed"]} / {pages_discovered} |
| Summary records fetched | {enumeration["summary_records_fetched"]} |
| Unique provider IDs | {enumeration["unique_provider_ids"]} |
| Duplicate IDs | {enumeration["duplicate_ids"]} |
| Invalid records | {enumeration["invalid_records"]} |
| Pages remaining | {pages_remaining} |

## Detail hydration

| Measure | Count |
|---|---:|
| IDs requiring hydration | {hydration["total_ids"]} |
| Detail responses accepted | {hydration["successful_detail_responses"]} |
| HTTP 304 | {hydration["http_304"]} |
| HTTP 404 | {hydration["http_404"]} |
| HTTP 429 | {hydration["http_429"]} |
| HTTP 5xx | {hydration["http_5xx"]} |
| Network/validation failures | {hydration["network_failures"]} |
| Pending | {hydration["pending_ids"]} |
| Failed | {hydration["failed_ids"]} |

## Local catalog

- Items before: {catalog["total_records_before"]}
- Items after: {catalog["total_records_after"]}
- New / updated / unchanged: {item_changes}
- Duplicate prevention events: {catalog["duplicate_prevention_count"]}
- Missing required level: {catalog["missing_required_level"]}
- Missing normalized statistics: {catalog["missing_statistics"]}
- Missing normalized restrictions: {catalog["missing_restrictions"]}
- Items with acquisition rows: {catalog["acquisition_information"]}
- Stored summary / detail payloads: {catalog["raw_summary_payloads"]} /
  {catalog["raw_detail_payloads"]}

### Verification status

{json.dumps(catalog["verification_status_counts"], indent=2)}

### Equipment slots

{json.dumps(catalog["equipment_slot_counts"], indent=2, ensure_ascii=False)}

### Required-level ranges

{json.dumps(catalog["required_level_ranges"], indent=2)}

> Imported records are not automatically verified. Data marked unknown remains unknown.
> This report summarizes the import and does not redistribute provider records.

Last error: {report["last_error"] or "none"}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forever-bis-full-catalog")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("enumerate", "Enumerate and persist every documented list page"),
        ("hydrate", "Hydrate all discovered provider IDs"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--job-id", type=int)
        command.add_argument("--confirm-write", action="store_true")
        if name == "enumerate":
            command.add_argument("--per-page", type=int, default=MAX_PAGE_SIZE)
        else:
            command.add_argument(
                "--retry-not-found",
                action="store_true",
                help="Retry previous detail HTTP 404 outcomes once in this run",
            )
    full = commands.add_parser("full", help="Enumerate then hydrate sequentially")
    full.add_argument("--job-id", type=int)
    full.add_argument("--confirm-write", action="store_true")
    full.add_argument("--workers", type=int, default=2)
    full.add_argument("--retry-not-found", action="store_true")
    status = commands.add_parser("status", help="Show import job status")
    status.add_argument("--job-id", type=int)
    report = commands.add_parser("report", help="Write JSON and Markdown coverage reports")
    report.add_argument("--job-id", type=int, required=True)
    report.add_argument("--json", type=Path)
    report.add_argument("--markdown", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {"enumerate", "hydrate", "full"} and not args.confirm_write:
        parser.error("database writes require --confirm-write")
    if args.command == "enumerate" and not 1 <= args.per_page <= MAX_PAGE_SIZE:
        parser.error(f"--per-page must be between 1 and {MAX_PAGE_SIZE}")
    if args.command == "full" and not 1 <= args.workers <= 4:
        parser.error("--workers must be between 1 and 4")

    engine = create_database_engine(get_settings())
    factory = create_session_factory(engine)
    provider = TheWoWDBProvider()
    try:
        with factory() as session:
            if args.command == "enumerate":
                report = enumerate_full_catalog(
                    session,
                    provider,
                    job_id=args.job_id,
                    per_page=args.per_page,
                )
            elif args.command == "hydrate":
                report = hydrate_full_catalog(
                    session,
                    provider,
                    job_id=args.job_id,
                    retry_not_found=args.retry_not_found,
                )
            elif args.command == "full":
                if args.job_id is None:
                    job = create_catalog_job(session, provider)
                    job_id = job.id
                else:
                    job_id = args.job_id
                job = session.get(FullCatalogImportJob, job_id)
                if job is None:
                    parser.error(f"Full-catalog job {job_id} was not found")
                if job.stage == "enumeration":
                    enumeration = enumerate_full_catalog(session, provider, job_id=job_id)
                else:
                    stored = full_catalog_report(session, job_id)["enumeration"]
                    enumeration = {
                        **stored,
                        "job_id": job_id,
                        "status": job.status,
                        "stage": job.stage,
                        "enumeration_complete": stored["complete"],
                    }
                if not enumeration.get("enumeration_complete"):
                    report = {"enumeration": enumeration, "job_id": job_id}
                else:
                    report = {
                        "status": "running",
                        "enumeration": enumeration,
                        "hydration": hydrate_full_catalog(
                            session,
                            provider,
                            job_id=job_id,
                            workers=args.workers,
                            retry_not_found=args.retry_not_found,
                        ),
                    }
                    report["status"] = report["hydration"]["status"]
            elif args.command == "status":
                job = (
                    session.get(FullCatalogImportJob, args.job_id)
                    if args.job_id
                    else session.scalar(
                        select(FullCatalogImportJob).order_by(FullCatalogImportJob.id.desc())
                    )
                )
                if job is None:
                    parser.error("No full-catalog import jobs exist")
                report = full_catalog_report(session, job.id)
            else:
                report = full_catalog_report(session, args.job_id, include_remaining_ids=True)
                report["generated_at"] = (
                    __import__("datetime").datetime.now().astimezone().isoformat()
                )
                json_path = (
                    args.json or Path("docs/reports") / f"thewowdb-full-catalog-{args.job_id}.json"
                )
                md_path = (
                    args.markdown
                    or Path("docs/reports") / f"thewowdb-full-catalog-{args.job_id}.md"
                )
                json_path.parent.mkdir(parents=True, exist_ok=True)
                md_path.parent.mkdir(parents=True, exist_ok=True)
                json_path.write_text(
                    json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                md_path.write_text(_report_markdown(report), encoding="utf-8")
                print(f"JSON report: {json_path}")
                print(f"Markdown report: {md_path}")
    except Exception as exc:
        logging.getLogger(__name__).exception("Full catalog operation failed: %s", exc)
        return 2
    finally:
        engine.dispose()
    if args.command == "report":
        print(
            json.dumps(
                {
                    "job_id": report["job_id"],
                    "status": report["status"],
                    "enumeration_complete": report["enumeration"]["complete"],
                    "pages_completed": report["enumeration"]["pages_completed"],
                    "unique_provider_ids": report["enumeration"]["unique_provider_ids"],
                    "hydration_complete": report["hydration"]["complete"],
                    "hydration_counts": {
                        "successful_detail_responses": report["hydration"][
                            "successful_detail_responses"
                        ],
                        "http_404": report["hydration"]["http_404"],
                        "pending": report["hydration"]["pending_ids"],
                        "failed": report["hydration"]["failed_ids"],
                    },
                },
                indent=2,
            )
        )
        return 0
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    if report.get("status") in {"completed", "enumerated"} or report.get("enumeration_complete"):
        return 0
    if report.get("hydration", {}).get("status") == "completed":
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
