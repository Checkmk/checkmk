#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import cmk.base.console as console

_profile = None
_profile_path = Path("profile.out")


def enable():
    # type: () -> None
    global _profile
    import cProfile  # pylint: disable=import-outside-toplevel
    _profile = cProfile.Profile()
    _profile.enable()
    console.verbose("Enabled profiling.\n")


def enabled():
    # type: () -> bool
    return _profile is not None


def output_profile():
    # type: () -> None
    if not _profile:
        return

    _profile.dump_stats(str(_profile_path))
    show_profile = _profile_path.with_name("show_profile.py")

    # TODO Change shebang as soon as we migrate to Python 3
    with show_profile.open("w") as f:
        f.write("""#!/usr/bin/env python
import sys
import pstats
try:
    profile_file = sys.argv[1]
except IndexError:
    profile_file = %s
stats = pstats.Stats(profile_file)
stats.sort_stats('time').print_stats()""" % _profile_path)

    show_profile.chmod(0o755)
    console.output("Profile '%s' written. Please run %s.\n" % (_profile_path, show_profile),
                   stream=sys.stderr)
