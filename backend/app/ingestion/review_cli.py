"""Local operator moderation CLI; intentionally not exposed as a public API."""

from __future__ import annotations

import argparse
import getpass
from uuid import UUID

from sqlalchemy import select

from backend.app.community.service import review_suggestion
from backend.app.core.config import get_settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.models.operations import ItemSuggestion


def main() -> int:
    parser = argparse.ArgumentParser(prog="forever-bis-review")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("pending", help="List pending community contributions")
    decide = commands.add_parser("decide", help="Record a local review decision")
    decide.add_argument("suggestion_id", type=UUID)
    decide.add_argument("decision", choices=("approved", "rejected", "needs_info"))
    decide.add_argument("--notes", default=None)
    args = parser.parse_args()
    engine = create_database_engine(get_settings())
    try:
        with create_session_factory(engine)() as session:
            if args.command == "pending":
                rows = session.scalars(
                    select(ItemSuggestion)
                    .where(ItemSuggestion.status.in_(["pending_review", "needs_info"]))
                    .order_by(ItemSuggestion.submitted_at)
                )
                for row in rows:
                    print(
                        f"{row.id} | {row.status} | {row.class_name}/{row.specialization} "
                        f"| {row.faction} L{row.character_level} | {row.equipment_slot} "
                        f"| {row.suggested_item_name} | {row.submitted_url} "
                        f"| duplicate={row.duplicate_flagged} "
                        f"| explanation={row.explanation or ''} "
                        f"| evidence={row.supporting_evidence or ''}"
                    )
            else:
                row = review_suggestion(
                    session,
                    args.suggestion_id,
                    decision=args.decision,
                    reviewer_identity=getpass.getuser(),
                    notes=args.notes,
                )
                print(f"Suggestion {row.id}: {row.status}; reviewer={row.reviewer_identity}")
                print("Approval does not verify or import the suggested item.")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
