#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
import dataclasses
import errno
import shutil
import tarfile
import tempfile
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from cmk.ccc import tar_archive

# The relay's 5 MB cap is a cleanup threshold applied after forwarding, so it does not
# bound a single crash: crash.info carries local_vars truncated at 5 MB, then base64'd.
_CRASH_LIMITS = tar_archive.ArchiveLimits(
    raw_limit_bytes=16 * 1024 * 1024,
    size_limit_bytes=32 * 1024 * 1024,
)


class UndecodableCrashArchiveError(Exception):
    pass


class CrashExtractionTimeoutError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class StoreCrashReportHandler:
    crashes_base: Path
    timeout: float

    async def process(self, *, crash_type: str, crash_id: str, archive: bytes) -> None:
        """Raises UndecodableCrashArchiveError for a per-crash problem, OSError for a
        site-wide one, and CrashExtractionTimeoutError past the timeout.

        The caller must keep those apart: a relay deletes its copy only on the first;
        the other two leave the endpoint as a non-terminal status, so the relay keeps
        its copy and retries. `TimeoutError` is itself an `OSError` subclass, so an
        `_store` failure that happens to carry a timeout errno (e.g. a stalled
        network-backed crashes_base) is reported as the timeout rather than as a
        plain site-wide one -- harmless here since both are non-terminal.
        """
        # Off the loop: unpacking a crash stalls every other request for 5-25 ms. Crashes
        # are rare, so they share the default threads instead of keeping a pool of their own.
        try:
            async with asyncio.timeout(self.timeout):
                await run_in_threadpool(self._store, crash_type, crash_id, archive)
        except TimeoutError as e:
            # The relay keeps the crash on a 503 and retries.
            raise CrashExtractionTimeoutError from e

    def _store(self, crash_type: str, crash_id: str, archive: bytes) -> None:
        target_dir = self.crashes_base / crash_type / crash_id
        # A re-send of a crash already stored. Keyed on crash.info rather than the dir,
        # so a dir the consolidation cron emptied but failed to remove is refilled.
        if (target_dir / "crash.info").is_file():
            return

        # Outside crashes_base, where the consolidation cron reads every dir as a crash
        # type and would drop its lock file into this one -- the rename below would then
        # move that lock into the stored crash. Staging sits beside crashes/, under the
        # same var/check_mk, so the rename is not cross-device.
        staging = Path(tempfile.mkdtemp(dir=self.crashes_base.parent))
        try:
            try:
                with tar_archive.open_bytes_streaming(archive, limits=_CRASH_LIMITS) as tar:
                    tar.extractall(staging)  # nosec B202 # BNS:481b41
            # tar_archive raises ValueError subclasses; tarfile compression and filter
            # errors come through raw, as does its ord() TypeError on a gzip header cut
            # after the method byte.
            except (ValueError, tarfile.TarError, TypeError) as e:
                raise UndecodableCrashArchiveError(repr(e)) from e

            target_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                staging.rename(target_dir)
            except OSError as e:
                # A re-send that raced the check above, or a target left non-empty by a
                # partial cleanup: rename cannot replace a non-empty dir, and rename(2)
                # lets the filesystem pick either errno.
                if e.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                    raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
