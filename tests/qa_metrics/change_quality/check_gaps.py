#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Reconcile recorded change-quality rows against git history; exit 1 on a gap.

Intended as a cheap daily cron on a *full* clone. It answers one question:
"is every fix-werk that ``push.py --full`` would record already present in
``cmk_change_tested`` for this branch?" -- i.e. did the incremental nightly (or
a too-shallow CI checkout) silently fall behind?

Unlike ``push.py`` this does **no** component / gerrit / cmk-components work: it
only compares the *set of werk_ids* the pusher would derive against the set
already stored. That keeps it fast and dependency-light (one git walk + one DB
query), and -- because it reuses ``walk_werk_adds`` and the same ``.werks`` +
werk-class gate as ``build_row`` -- it cannot drift from the pusher's definition
of "should be recorded".

Because ``--full`` is only ever run by hand here, nothing else notices when a
gap opens. This is that missing signal: cron it daily and let a non-zero exit
mail you.

Exit codes: 0 = in sync (or skipped because the DB was unreachable, e.g. VPN
down -- a daily cron shouldn't alarm on that), 1 = gap found (werks in git
missing from the DB), 2 = usage / environment error.
"""

import argparse
import logging
import subprocess
import sys
from collections.abc import Container, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Final

import psycopg

from cmk.werks.tool.models import Class
from cmk.werks.tool.utils import load_raw_files
from tests.qa_metrics.change_quality import walk
from tests.qa_metrics.change_quality.repo import read_branch_version
from tests.qa_metrics.change_quality.rows import CHANGE_TESTED
from tests.qa_metrics.db import MetabasePostgres

logger = logging.getLogger(__name__)

# The pusher (push.py) records only these werk classes, and is run with its
# default in every environment (nothing passes --werk-classes). The check
# mirrors that here rather than exposing a knob that, set differently from the
# pusher, would only ever manufacture false gaps. One line to change if the
# pusher's policy ever does.
_WERK_CLASSES: Final = frozenset({Class.FIX})

# Cap on how many missing ids we spell out; the count is what matters for an
# alert, the sample is just for a quick eyeball.
_MAX_REPORTED: Final = 25


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Surface change-quality werks missing from cmk_change_tested."
    )
    parser.add_argument("--repo", type=Path, required=True, help="Path to a checkmk worktree")
    parser.add_argument(
        "--since",
        type=_parse_date,
        default=None,
        metavar="YYYY-MM-DD",
        help="Only reconcile werks added on/after this date. Bounds the git "
        "walk so a daily cron stays cheap; omit to scan all history (do that "
        "once to establish a baseline). Recorded rows are always compared in "
        "full, so bounding the walk can only miss *old* gaps, never invent one.",
    )
    parser.add_argument(
        "--grace-days",
        type=int,
        default=2,
        metavar="N",
        help="Ignore werks added within the last N days (default: 2). Werks "
        "merged since the last nightly push legitimately aren't in the DB yet; "
        "without this grace the cron would false-alarm on them every morning. "
        "N must comfortably exceed one nightly-push cycle.",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def expected_werk_ids(
    repo: Path, allowed_classes: Container[Class], *, since: date | None, until: date | None
) -> set[int]:
    """werk_ids the pusher would record for werk-add commits on HEAD.

    Mirrors ``push.build_row``'s gate exactly: a werk-add event counts only if
    the werk still exists under ``.werks`` at HEAD and its class is allowed.
    ``until`` excludes the just-merged tail the nightly push hasn't reached yet.
    """
    werks_index = {w.id: w for w in load_raw_files(repo / ".werks")}
    ids: set[int] = set()
    for event in walk.walk_werk_adds(repo, since=since, until=until):
        werk = werks_index.get(event.werk_id)
        if werk is not None and werk.class_ in allowed_classes:
            ids.add(werk.id)
    return ids


def recorded_werk_ids(db: MetabasePostgres, branch: str) -> set[int]:
    """werk_ids already stored in ``cmk_change_tested`` for ``branch``."""
    with db.cursor() as cursor:
        cursor.execute(
            f'SELECT werk_id FROM "{CHANGE_TESTED.name}" WHERE branch = %s',
            (branch,),
        )
        return {row[0] for row in cursor.fetchall()}


def find_gap(
    repo: Path,
    branch: str,
    allowed_classes: Container[Class],
    *,
    since: date | None,
    until: date | None,
) -> list[int]:
    """Return sorted werk_ids present in git history but missing from the DB."""
    expected = expected_werk_ids(repo, allowed_classes, since=since, until=until)
    with MetabasePostgres.from_env() as db:
        recorded = recorded_werk_ids(db, branch)
    return sorted(expected - recorded)


def _report_config_error(message: str) -> None:
    """Log a one-line config/environment error (no traceback -- cron-mail
    friendly). A plain helper rather than ``logging.error`` inside the ``except``
    body, which the linter would flag (TRY400)."""
    logger.error("Cannot run check: %s", message)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    class_label = "/".join(sorted(c.value for c in _WERK_CLASSES))

    try:
        logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
        branch = read_branch_version(args.repo)
        # Exclude the just-merged tail the nightly push may not have reached yet.
        until = date.today() - timedelta(days=args.grace_days)
        missing = find_gap(args.repo, branch, _WERK_CLASSES, since=args.since, until=until)
    except psycopg.OperationalError as e:
        if e.sqlstate is None:
            # No SQLSTATE => we never reached the server (host unreachable /
            # connection refused / DNS failure) -- typically the VPN is down.
            # Not a gap and not a config error: skip quietly and exit 0 so the
            # daily cron stays silent (it mails only on non-zero).
            logger.warning("Skipping check: QA metrics database is unreachable (VPN down?). %s", e)
            return 0
        # The server answered with an error (bad credentials, missing database,
        # ...): a real configuration problem worth surfacing.
        _report_config_error(str(e))
        return 2
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        # Everything else that is a setup problem rather than a gap: missing
        # POSTGRES_* / QA_POSTGRES_* env vars, incomplete DB auth config, no
        # BRANCH_VERSION in defines.make, a bad --log-level, or --repo not being
        # a git repo. Surface as a config error (exit 2) -- never let it escape
        # main and become an uncaught-exception exit 1, which reads as "gap".
        _report_config_error(str(e))
        return 2

    if missing:
        logger.error(
            "GAP: %d %s-werk(s) in git history are missing from %s for branch %s. "
            "Run `tests/run_tests.sh qa-metrics-change-quality-full` to backfill. "
            "Missing werk_ids (first %d): %s",
            len(missing),
            class_label,
            CHANGE_TESTED.name,
            branch,
            min(len(missing), _MAX_REPORTED),
            missing[:_MAX_REPORTED],
        )
        return 1

    logger.info(
        "OK: every %s-werk on branch %s is recorded in %s.",
        class_label,
        branch,
        CHANGE_TESTED.name,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
