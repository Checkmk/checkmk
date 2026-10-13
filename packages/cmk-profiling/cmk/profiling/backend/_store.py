#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""On-disk schema for the shared performance-profile store.

Used by both the GUI (cmk/profiling/gui/_store.py) and cmk --profile
(cmk/base/profiling.py) so the two writers cannot drift on the file layout.
Each profile is stored as a pair:

    {profile_id}.profile   — raw cProfile marshal dump
    {profile_id}.json      — metadata sidecar

The ``.json`` sidecar is written last through an atomic rename, so a crash
between the two writes leaves at most an orphan ``.profile`` (invisible to
listing; cleaned up by ``enforce_retention``).
"""

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, TypedDict

from cmk.ccc.store import save_bytes_to_file, save_text_to_file

logger = logging.getLogger(__name__)

PROFILE_SUFFIXES = (".profile", ".json")
# 12 hex chars of uuid4 entropy give a comfortable margin against collisions
# when multiple WSGI workers profile requests in the same second.
PROFILE_ID_RE = re.compile(r"^[0-9]{8}_[0-9]{6}_[a-f0-9]{12}$")

DEFAULT_MAX_PROFILES = 100

SourceType = Literal["gui_request", "file_upload", "base_command"]


class ProfilingOptions(TypedDict, total=False):
    """Shape of the ``profiling_options`` global setting (see the matching valuespec)."""

    enabled: bool
    max_count: int
    max_age_days: int


@dataclass
class ProfileMetadata:
    profile_id: str
    timestamp: str
    source_type: SourceType
    source_info: str
    duration_ms: float | None

    @staticmethod
    def from_json(path: Path) -> ProfileMetadata:
        return ProfileMetadata(**json.loads(path.read_text(encoding="utf-8")))


def new_profile_id(now: datetime | None = None) -> tuple[str, datetime]:
    now = now or datetime.now()
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:12]}", now


def write_profile(
    profiles_dir: Path,
    *,
    profile_bytes: bytes,
    source_type: SourceType,
    source_info: str,
    duration_ms: float | None,
) -> str:
    """Write a profile + metadata pair and return the generated id.

    The ``.profile`` is written first, the ``.json`` second; both through the
    atomic-rename semantics of ``cmk.ccc.store``. A crash between the two
    leaves only an orphan ``.profile`` which ``enforce_retention`` will reap.
    """
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_id, now = new_profile_id()
    save_bytes_to_file(profiles_dir / f"{profile_id}.profile", profile_bytes)
    save_text_to_file(
        profiles_dir / f"{profile_id}.json",
        json.dumps(
            asdict(
                ProfileMetadata(
                    profile_id=profile_id,
                    timestamp=now.isoformat(),
                    source_type=source_type,
                    source_info=source_info,
                    duration_ms=duration_ms,
                )
            ),
            indent=2,
        ),
    )
    return profile_id


def list_metadata(profiles_dir: Path) -> list[ProfileMetadata]:
    if not profiles_dir.is_dir():
        return []
    profiles: list[ProfileMetadata] = []
    for meta_file in sorted(profiles_dir.glob("*.json"), reverse=True):
        try:
            profiles.append(ProfileMetadata.from_json(meta_file))
        except Exception:
            logger.warning("Skipping corrupt metadata: %(meta_file)s", {"meta_file": meta_file})
    return profiles


def get_metadata(profiles_dir: Path, profile_id: str) -> ProfileMetadata | None:
    if not PROFILE_ID_RE.match(profile_id):
        return None
    path = profiles_dir / f"{profile_id}.json"
    if not path.is_file():
        return None
    try:
        return ProfileMetadata.from_json(path)
    except Exception:
        return None


def get_profile_path(profiles_dir: Path, profile_id: str) -> Path | None:
    if not PROFILE_ID_RE.match(profile_id):
        return None
    path = profiles_dir / f"{profile_id}.profile"
    return path if path.is_file() else None


def delete_profile(profiles_dir: Path, profile_id: str) -> bool:
    if not PROFILE_ID_RE.match(profile_id):
        return False
    found = False
    for suffix in PROFILE_SUFFIXES:
        path = profiles_dir / f"{profile_id}{suffix}"
        try:
            path.unlink()
            found = True
        except FileNotFoundError:
            pass
    return found


def delete_all_profiles(profiles_dir: Path) -> int:
    if not profiles_dir.is_dir():
        return 0
    count = 0
    for meta_file in profiles_dir.glob("*.json"):
        profile_id = meta_file.stem
        if not PROFILE_ID_RE.match(profile_id):
            continue
        for suffix in PROFILE_SUFFIXES:
            (profiles_dir / f"{profile_id}{suffix}").unlink(missing_ok=True)
        count += 1
    # Also wipe any orphan .profile files that lost their sidecar.
    for profile_file in profiles_dir.glob("*.profile"):
        if not PROFILE_ID_RE.match(profile_file.stem):
            continue
        profile_file.unlink(missing_ok=True)
    return count


def enforce_retention(
    profiles_dir: Path,
    *,
    max_count: int = DEFAULT_MAX_PROFILES,
    max_age_days: int | None = None,
) -> int:
    """Trim the store by age and/or count; clean up orphan ``.profile`` files.

    Only the caller's own process should invoke this — the filesystem
    operations are idempotent but not synchronized across concurrent callers.
    Callers that need coordination should wrap this in ``cmk.ccc.store.locked``
    on a dedicated lock file.
    """
    if not profiles_dir.is_dir():
        return 0

    meta_files = sorted(profiles_dir.glob("*.json"))
    removed = 0

    if max_age_days is not None and max_age_days > 0:
        cutoff = datetime.now() - timedelta(days=max_age_days)
        surviving: list[Path] = []
        for meta_file in meta_files:
            try:
                meta = ProfileMetadata.from_json(meta_file)
                if datetime.fromisoformat(meta.timestamp) < cutoff:
                    delete_profile(profiles_dir, meta.profile_id)
                    removed += 1
                    continue
            except Exception:
                logger.warning(
                    "Skipping corrupt metadata during housekeeping: %(meta_file)s",
                    {"meta_file": meta_file},
                )
            surviving.append(meta_file)
        meta_files = surviving

    excess = len(meta_files) - max_count
    if excess > 0:
        for oldest in meta_files[:excess]:
            profile_id = oldest.stem
            for suffix in PROFILE_SUFFIXES:
                (profiles_dir / f"{profile_id}{suffix}").unlink(missing_ok=True)
        removed += excess
        meta_files = meta_files[excess:]

    # Reap orphan .profile files whose sidecar never materialised (crash
    # between the two writes, or sidecar deleted out-of-band).
    known_ids = {f.stem for f in meta_files}
    for profile_file in profiles_dir.glob("*.profile"):
        if profile_file.stem not in known_ids:
            profile_file.unlink(missing_ok=True)

    return removed
