#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""A helper module to implement profiling functionalitiy. The main part
is to provide a contextmanager that can be added to existing code with
minimal changes."""

import cProfile
import sys
import time
from types import TracebackType  # pylint: disable=unused-import
from typing import Callable, Type, Union, Any, Optional  # pylint: disable=unused-import

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path

import cmk.utils.log


class Profile(object):
    def __init__(self, enabled=True, profile_file=None, **kwargs):
        # type: (bool, Union[Path, str], **Any) -> None

        if profile_file is None or isinstance(profile_file, Path):
            self._profile_file = profile_file
        else:
            self._profile_file = Path(profile_file)

        self._enabled = enabled
        self._kwargs = kwargs
        self._profile = None  # type: Optional[cProfile.Profile]

    def __enter__(self):
        # type: () -> Profile
        if self._enabled:
            cmk.utils.log.logger.info("Recording profile")
            self._profile = cProfile.Profile(**self._kwargs)
            self._profile.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        if not self._enabled:
            return

        if not self._profile:
            return

        self._profile.disable()

        if not self._profile_file:
            self._profile.print_stats()
            return

        self._write_profile()
        self._write_dump_script()

    def _write_profile(self):
        # type: () -> None
        if not self._profile:
            return
        self._profile.dump_stats(str(self._profile_file))
        cmk.utils.log.logger.info("Created profile file: %s", self._profile_file)

    def _write_dump_script(self):
        # type: () -> None
        if not self._profile_file:
            return

        script_path = self._profile_file.with_suffix(".py")
        with script_path.open("w", encoding="utf-8") as f:
            f.write(u"#!/usr/bin/env python\n"
                    "import pstats\n"
                    "stats = pstats.Stats(%r)\n"
                    "stats.sort_stats('time').print_stats()\n" % self._profile_file)
        script_path.chmod(0o755)
        cmk.utils.log.logger.info("Created profile dump script: %s", script_path)


def profile_call(base_dir, enabled=True):
    # type: (str, bool) -> Callable
    """
This decorator can be used to profile single functions as a starting point.
A directory where the file will be saved has to be stated as first argument.
Enabling/disabling as second argument is optional. By default it's enabled.
The name of the output file is composed of the function name itself,
the timestamp when the function was called and the suffix '.profile'.
Examples:
  @cmk.utils.profile.profile_call(base_dir="/PATH/TO/DIR")
  @cmk.utils.profile.profile_call(base_dir="/PATH/TO/DIR", enabled=True)
  @cmk.utils.profile.profile_call(base_dir="/PATH/TO/DIR", enabled=False)
"""
    def decorate(f):
        def wrapper(*args, **kwargs):
            filepath = "%s/%s_%s.profile" % \
                (base_dir.rstrip("/"), f.__name__, time.time())
            with Profile(enabled=enabled, profile_file=filepath):
                return f(*args, **kwargs)

        return wrapper

    return decorate
