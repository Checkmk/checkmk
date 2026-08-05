#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import marshal
import sys
import time
from contextlib import suppress
from pathlib import Path

from ._store import enforce_retention, write_profile

_profile = None
_start_time: float | None = None


def enable() -> None:
    global _profile, _start_time
    import cProfile

    _profile = cProfile.Profile()
    _start_time = time.monotonic()
    _profile.enable()


def enabled() -> bool:
    return _profile is not None


def output_profile(profiles_dir: Path) -> None:
    if _profile is None:
        return

    duration_ms = None if _start_time is None else round((time.monotonic() - _start_time) * 1000, 2)

    # Retention here uses the shared-module default rather than reading the GUI's
    # ``profiling_options`` global setting — cmk/base does not depend on cmk/gui
    # runtime config. The GUI reconciles to the configured cap on the next save
    # or page load.
    _profile.create_stats()
    try:
        profile_id = write_profile(
            profiles_dir,
            profile_bytes=marshal.dumps(_profile.stats),
            source_type="base_command",
            source_info=" ".join(sys.argv),
            duration_ms=duration_ms,
        )
        enforce_retention(profiles_dir)
    except OSError as e:
        with suppress(OSError):
            sys.stderr.write(f"Failed to write profile to {profiles_dir}: {e}\n")
            sys.stderr.flush()
        return

    # Tell the CLI user where the dump landed: the GUI viewer is only reachable
    # when the performance-profiles feature is enabled, so the path is the only
    # pointer available otherwise.
    with suppress(OSError):
        sys.stderr.write(f"Profile written to {profiles_dir / f'{profile_id}.profile'}\n")
        sys.stderr.flush()
