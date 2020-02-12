#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
