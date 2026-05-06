#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Push change-tested rows to the QA Metabase postgres.

One row per (werk_id, branch). Cherry-picks of the same werk into multiple
branches produce one row per branch.

Idempotency: the only state mutation is an UPSERT keyed on (werk_id, branch);
re-runs converge.

Run as a module to keep absolute imports working::

    python -m tests.qa_metrics.change_quality.push --repo <path> --branch <name>
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Final, TextIO

from cmk.werks.models import Class, WerkV3
from cmk.werks.utils import load_raw_files
from tests.qa_metrics.change_quality import components, detect_test, walk
from tests.qa_metrics.change_quality.repo import read_branch_version
from tests.qa_metrics.change_quality.rows import CHANGE_TESTED, ChangeTestedRow
from tests.qa_metrics.change_quality.state import read_watermark
from tests.qa_metrics.db import MetabasePostgres

logger = logging.getLogger(__name__)

WERK_CLASSES: Final = {c.value: c for c in Class}


def _parse_classes(raw: str) -> list[Class]:
    classes: list[Class] = []
    for token in raw.split(","):
        normalised = token.strip().lower()
        if normalised not in WERK_CLASSES:
            raise argparse.ArgumentTypeError(
                f"Unknown werk class {normalised!r}; valid: {sorted(WERK_CLASSES)}"
            )
        classes.append(WERK_CLASSES[normalised])
    if not classes:
        raise argparse.ArgumentTypeError("--werk-classes must list at least one class")
    return classes


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push per-werk test-inclusion rows to cmk_change_tested.",
    )
    parser.add_argument("--repo", type=Path, required=True, help="Path to a checkmk worktree")
    parser.add_argument(
        "--branch",
        type=str,
        default=None,
        help="Branch label to store; defaults to BRANCH_VERSION from the "
        "worktree's defines.make (e.g. '2.6.0').",
    )
    parser.add_argument(
        "--from", dest="from_date", type=_parse_date, default=None, metavar="YYYY-MM-DD"
    )
    parser.add_argument(
        "--to", dest="to_date", type=_parse_date, default=None, metavar="YYYY-MM-DD"
    )
    parser.add_argument(
        "--werk-classes",
        type=_parse_classes,
        default=[Class.FIX],
        help="Comma-separated subset of: fix,feature,security (default: fix)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute rows but skip DB writes")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Walk all of git history. Without this, the script reads the "
        "latest commit_time already in `cmk_change_tested` for the target "
        "branch and only walks newer commits. Pass --full after changing "
        "the metric definition (walk.py / detect_test.py / components.py / "
        "rows.py) so every existing row is re-derived under the new logic.",
    )
    parser.add_argument(
        "--format",
        choices=["log", "csv", "json"],
        default="log",
        help="Row dump format. 'log' (default) prints 5 sample lines under "
        "--dry-run only. 'csv' / 'json' emit every row to stdout (or --output) "
        "regardless of --dry-run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="With --format csv|json, write to this file instead of stdout.",
    )
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Append timestamped log entries to this file (in addition to stdout).",
    )
    return parser.parse_args(argv)


_HEARTBEAT_EVERY = 1000


def _setup_logging(level: str, log_file: Path | None) -> None:
    logging.basicConfig(level=level)
    if log_file is None:
        return
    handler = logging.FileHandler(log_file)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    logging.getLogger().addHandler(handler)


def _heartbeat(i: int, total: int) -> None:
    """Write a `.` to stdout every _HEARTBEAT_EVERY rows. No-op for short runs."""
    if total <= _HEARTBEAT_EVERY:
        return
    if i % _HEARTBEAT_EVERY == 0:
        sys.stdout.write(".")
        sys.stdout.flush()


def _emit_rows(rows: Iterable[ChangeTestedRow], fmt: str, output: Path | None) -> None:
    """Write ``rows`` to ``output`` (or stdout) in ``csv`` / ``json``."""
    rows_list = list(rows)
    if output is not None:
        with output.open("w", encoding="utf-8") as sink:
            _write_rows(rows_list, fmt, sink)
        logger.info("Wrote %d rows to %s (%s)", len(rows_list), output, fmt)
    else:
        _write_rows(rows_list, fmt, sys.stdout)


def _write_rows(rows: list[ChangeTestedRow], fmt: str, sink: TextIO) -> None:
    if fmt == "csv":
        _write_csv(sink, rows)
    elif fmt == "json":
        _write_json(sink, rows)


def _write_csv(sink: TextIO, rows: list[ChangeTestedRow]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].to_db_dict().keys())
    writer = csv.DictWriter(sink, fieldnames=fieldnames, dialect="unix")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _csv_value(v) for k, v in row.to_db_dict().items()})


def _csv_value(v: object) -> object:
    return v.isoformat() if isinstance(v, datetime) else v


def _write_json(sink: TextIO, rows: list[ChangeTestedRow]) -> None:
    json.dump(
        [row.to_db_dict() for row in rows],
        sink,
        default=_json_default,
        indent=2,
    )
    sink.write("\n")


def _json_default(o: object) -> str:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Not JSON serialisable: {type(o).__name__}")


def build_row(
    branch: str,
    werk_add: walk.WerkAdd,
    werks_index: dict[int, WerkV3],
    allowed_classes: set[Class],
    component_map: dict[str, str | None],
) -> ChangeTestedRow | None:
    werk = werks_index.get(werk_add.werk_id)
    if werk is None or werk.class_ not in allowed_classes:
        return None
    info = werk_add.commit
    return ChangeTestedRow(
        werk_id=werk.id,
        branch=branch,
        werk_class=werk.class_.value,
        werk_component=werk.component,
        werk_date=werk.date,
        edition=werk.edition.value,
        level=werk.level.value,
        title=werk.title,
        git_commit_hash=info.sha,
        commit_time=info.commit_time,
        author_email=info.author_email or None,
        subject=info.subject or None,
        gerrit_change_id=info.gerrit_change_id,
        source_component=components.pick_component(info.files_changed, component_map),
        has_test=detect_test.attribute_test_for_change(info.files_changed),
        files_changed=len(info.files_changed),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    _setup_logging(args.log_level, args.log_file)

    branch = args.branch or read_branch_version(args.repo)

    logger.info("Indexing werks from %s/.werks", args.repo)
    werks_index = {w.id: w for w in load_raw_files(args.repo / ".werks")}
    allowed_classes = set(args.werk_classes)

    # Incremental mode: read the DB watermark for this branch and walk only
    # commits since then. Skipped under --full / --dry-run / explicit --from.
    if not args.full and not args.dry_run and args.from_date is None:
        with MetabasePostgres.from_env() as db:
            args.from_date = read_watermark(db, branch)
        if args.from_date is not None:
            logger.info(
                "Incremental mode: walking commits since %s. "
                "Re-run with `make qa-metrics-change-quality-full` (--full) "
                "after changing the metric definition to recompute every row.",
                args.from_date,
            )
        else:
            logger.info(
                "Incremental mode: no prior rows for branch %s; walking all of history.",
                branch,
            )
    elif args.full:
        logger.info("Full mode: walking all of git history.")

    logger.info("Walking git history for werk-add events")
    events = list(walk.walk_werk_adds(args.repo, since=args.from_date, until=args.to_date))

    unique_paths = {
        path
        for event in events
        for path in event.commit.files_changed
        if not detect_test.is_test_path(path)
    }
    component_map = components.lookup_components(unique_paths, args.repo)

    total = len(events)
    rows: list[ChangeTestedRow] = []
    for i, werk_add in enumerate(events, start=1):
        row = build_row(branch, werk_add, werks_index, allowed_classes, component_map)
        if row is not None:
            rows.append(row)
        _heartbeat(i, total)
    if total > _HEARTBEAT_EVERY:
        sys.stdout.write("\n")
        sys.stdout.flush()

    logger.info(
        "Saw %d werk-add events; built %d rows for classes %s",
        len(events),
        len(rows),
        [c.value for c in args.werk_classes],
    )

    if args.format != "log":
        _emit_rows(rows, args.format, args.output)

    if args.dry_run:
        logger.info("--dry-run: not writing to DB")
        if args.format == "log":
            for row in rows[:5]:
                logger.info(
                    "sample: werk_id=%s class=%s has_test=%s",
                    row.werk_id,
                    row.werk_class,
                    row.has_test,
                )
        return 0

    with MetabasePostgres.from_env() as db:
        CHANGE_TESTED.apply_schema(db)
        for row in rows:
            CHANGE_TESTED.upsert(db, row)
    logger.info("Pushed %d rows to %s", len(rows), CHANGE_TESTED.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
