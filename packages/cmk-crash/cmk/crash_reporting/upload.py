#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Batch upload of on-disk crash reports to crash.checkmk.com.

Upload flow: discover → POST each → classify. Crash dirs are never deleted by the
uploader. SUCCESS and REJECTED outcomes get a `.uploaded` marker so the backlog
drains across cron ticks instead of re-uploading the same crashes forever;
TRANSIENT outcomes are left unmarked and retried next tick.
cleanup_crash_reports() handles eventual eviction by age and disk budget.

Callers pass site identity and config; this module has no knowledge of global.mk,
ConfigDomain settings, or OMD paths. Those are wired by the CLI.
"""

import enum
import logging
from collections import defaultdict
from collections.abc import Mapping
from itertools import islice
from pathlib import Path
from urllib.parse import urlsplit

import requests

from cmk.crash import iter_crash_dirs

from ._packaging import crash_report_submit_payload

logger = logging.getLogger("cmk.crash_reporting.upload")

_POST_TIMEOUT = 30  # seconds per crash POST

# Sentinel left in a crash dir after a terminal (SUCCESS or REJECTED) upload attempt.
# The crash dir and its contents are left on disk untouched. Cleanup_crash_reports()
# still evicts it by age/size, and admins can still look up the crash ID.
_UPLOADED_MARKER = ".uploaded"


def _is_supported_upload_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and bool(parts.netloc)


class _UploadOutcome(enum.Enum):
    SUCCESS = "success"
    REJECTED = "rejected"  # server rejected — crash retained; cleanup handles eviction
    TRANSIENT = "transient"  # retain; retry on the next cron tick


def run_batch(
    *,
    crash_report_url: str,
    base_path: Path,
    name: str,
    mail: str,
    max_crashes: int = 50,
    dry_run: bool = False,
) -> None:
    """Upload up to max_crashes crash dirs from base_path (var/check_mk/crashes/)
    to crash_report_url. Non-HTTPS URLs are refused.

    Crash dirs are never deleted by this function. SUCCESS and REJECTED outcomes
    get a `.uploaded` marker so the backlog drains across runs; TRANSIENT
    outcomes are retried next tick. cleanup_crash_reports() handles eventual
    eviction by age and disk budget.
    """
    if not _is_supported_upload_url(crash_report_url):
        logger.error(
            "Refusing to POST crash reports to non-HTTPS URL: %(url)s",
            {"url": crash_report_url},
        )
        return

    outcome_counts: defaultdict[_UploadOutcome, int] = defaultdict(int)
    pending_crash_dirs = (
        crash_dir
        for crash_dir in iter_crash_dirs(base_path)
        if (crash_dir / "crash.info").exists() and not (crash_dir / _UPLOADED_MARKER).exists()
    )

    for crash_dir in islice(pending_crash_dirs, max_crashes):
        if dry_run:
            logger.info("Dry run: would upload crash_id=%(crash_id)s", {"crash_id": crash_dir.name})
            continue
        try:
            outcome = _upload_one(
                crash_report_url=crash_report_url,
                name=name,
                mail=mail,
                crash_dir=crash_dir,
            )
        except requests.exceptions.RequestException as exc:
            # Remaining crash dirs stay unmarked and get picked up on the next tick.
            logger.warning("Upload failed, stopping batch early: %(error)s", {"error": exc})
            break
        outcome_counts[outcome] += 1
        if outcome is not _UploadOutcome.TRANSIENT:
            try:
                (crash_dir / _UPLOADED_MARKER).touch(exist_ok=True)
            except OSError:
                logger.warning(
                    "Failed to mark crash as uploaded, may be retried crash_id=%(crash_id)s",
                    {"crash_id": crash_dir.name},
                )

    logger.info(
        "Crash upload summary: %(success)d uploaded, %(rejected)d rejected, %(transient)d left for retry",
        {
            "success": outcome_counts[_UploadOutcome.SUCCESS],
            "rejected": outcome_counts[_UploadOutcome.REJECTED],
            "transient": outcome_counts[_UploadOutcome.TRANSIENT],
        },
    )


def _serialize_crash_dir(crash_dir: Path) -> Mapping[str, bytes]:
    return {
        filepath.name: filepath.read_bytes()
        for filepath in sorted(crash_dir.iterdir())
        if filepath.is_file() and not filepath.name.startswith(".")
    }


def _upload_one(*, crash_report_url: str, name: str, mail: str, crash_dir: Path) -> _UploadOutcome:
    """Raises requests.exceptions.RequestException if the POST does not complete or the
    server asks us to retry later; the caller treats that as batch-fatal."""
    logger.info("uploading crash_id=%(crash_id)s", {"crash_id": crash_dir.name})
    try:
        serialized_crash_report = _serialize_crash_dir(crash_dir)
    except OSError:
        logger.warning(
            "Crash dir no longer accessible, skipping crash_id=%(crash_id)s",
            {"crash_id": crash_dir.name},
        )
        return _UploadOutcome.TRANSIENT
    payload = crash_report_submit_payload(
        name=name, mail=mail, serialized_crash_report=serialized_crash_report
    )
    resp = requests.post(
        crash_report_url, data=payload, timeout=_POST_TIMEOUT, allow_redirects=False
    )
    if resp.status_code == 429:  # "come back later" - must not be marked like the other 4xx
        resp.raise_for_status()
    if resp.status_code == 200:
        return _UploadOutcome.SUCCESS if resp.content.startswith(b"OK") else _UploadOutcome.REJECTED
    if 400 <= resp.status_code < 500:  # includes 413 (payload too large)
        return _UploadOutcome.REJECTED
    return _UploadOutcome.TRANSIENT  # 5xx or unexpected
