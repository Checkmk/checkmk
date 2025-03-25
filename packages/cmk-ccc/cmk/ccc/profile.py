#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005
"""A helper module to implement profiling functionalitiy. The main part
is to provide a contextmanager that can be added to existing code with
minimal changes."""

import cProfile
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import ParamSpec, TypeVar

logger = logging.getLogger("cmk.ccc.profile")


class Profile:
    def __init__(
        self,
        *,
        enabled: bool = True,
        profile_file: Path | str | None = None,
        # cProfile.Profile arguments, avoids the need for Any
        timer: Callable[[], float] | None = None,
        timeunit: float = 0.0,
        subcalls: bool = True,
        builtins: bool = True,
    ) -> None:
        self._enabled = enabled
        self._profile_file = (
            profile_file
            if profile_file is None or isinstance(profile_file, Path)
            else Path(profile_file)
        )
        self._timer = timer
        self._timeunit = timeunit
        self._subcalls = subcalls
        self._builtins = builtins
        self._profile: cProfile.Profile | None = None

    def __enter__(self) -> "Profile":
        if self._enabled:
            logger.info("Recording profile")
            # cProfile.Profile has a slightly interesting API: None is not allowed as a timer argument. o_O
            self._profile = (
                cProfile.Profile(
                    timeunit=self._timeunit,
                    subcalls=self._subcalls,
                    builtins=self._builtins,
                )
                if self._timer is None
                else cProfile.Profile(
                    timer=self._timer,
                    timeunit=self._timeunit,
                    subcalls=self._subcalls,
                    builtins=self._builtins,
                )
            )
            self._profile.enable()
        return self

    def __exit__(self, *exc_info: object) -> None:
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

    def _write_profile(self) -> None:
        if not self._profile:
            return
        self._profile.dump_stats(str(self._profile_file))
        logger.info("Created profile file: %s", self._profile_file)

    def _write_dump_script(self) -> None:
        if not self._profile_file:
            return

        script_path = self._profile_file.with_suffix(".py")
        with script_path.open("w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env python3\n"
                "import pstats\n"
                f'stats = pstats.Stats("{self._profile_file}")\n'
                "stats.sort_stats('cumtime').print_stats()\n"
            )
        script_path.chmod(0o755)
        logger.info("Created profile dump script: %s", script_path)


P = ParamSpec("P")
R = TypeVar("R")


def profile_call(base_dir: str, enabled: bool = True) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    This decorator can be used to profile single functions as a starting point.
    A directory where the file will be saved has to be stated as first argument.
    Enabling/disabling as second argument is optional. By default it's enabled.
    The name of the output file is composed of the function name itself,
    the timestamp when the function was called and the suffix '.profile'.
    Examples:
      @cmk.ccc.profile.profile_call(base_dir="/PATH/TO/DIR")
      @cmk.ccc.profile.profile_call(base_dir="/PATH/TO/DIR", enabled=True)
      @cmk.ccc.profile.profile_call(base_dir="/PATH/TO/DIR", enabled=False)"""

    def wrap(f: Callable[P, R]) -> Callable[P, R]:
        def wrapped_f(*args: P.args, **kwargs: P.kwargs) -> R:
            filepath = f"{base_dir.rstrip('/')}/{f.__name__}_{time.time()}.profile"
            with Profile(enabled=enabled, profile_file=filepath):
                return f(*args, **kwargs)

        return wrapped_f

    return wrap
