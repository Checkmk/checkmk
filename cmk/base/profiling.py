#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from contextlib import suppress
from pathlib import Path

from cmk.utils.log import console

_profile = None
_profile_path = Path("profile.out")


def enable() -> None:
    global _profile
    import cProfile

    _profile = cProfile.Profile()
    _profile.enable()
    console.verbose("Enabled profiling.")


def enabled() -> bool:
    return _profile is not None


def output_profile() -> None:
    if not _profile:
        return

    _profile.dump_stats(str(_profile_path))
    show_profile = _profile_path.with_name("show_profile.py")

    with show_profile.open("w") as f:
        f.write(
            """#!/usr/bin/env python3
import sys
import pstats
try:
    profile_file = sys.argv[1]
except IndexError:
    profile_file = "%s"
stats = pstats.Stats(profile_file)
stats.sort_stats('cumtime').print_stats()"""
            % _profile_path
        )

    show_profile.chmod(0o755)
    with suppress(IOError):
        sys.stderr.write(f"Profile '{_profile_path}' written. Please run {show_profile}.\n")
        sys.stderr.flush()
