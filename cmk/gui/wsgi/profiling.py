# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pathlib
from typing import Optional

from werkzeug.wrappers import Request

import cmk.gui.config
import cmk.utils.paths
import cmk.utils.log

from repoze.profile import ProfileMiddleware  # type: ignore[import]
from repoze.profile.compat import profile  # type: ignore[import]


class ProfileSwitcher:
    """Profile a WSGI application, configurable

    The behaviour can be changed upon setting config.profile to either
        * True: profiling always enabled
        * False: profiling always off
        * "enable_by_var":  profiling enabled when "_profile" query parameter present in request

    """
    def __init__(self, app, profile_file: Optional[pathlib.Path] = None):
        self.app = app
        if profile_file is None:
            profile_file = pathlib.Path(cmk.utils.paths.var_dir) / "multisite.profile"

        # If set to True, this accumulates the profiling data, instead of re-creating fresh files
        # on every request.
        self.accumulate = False
        self.profile_file = profile_file
        self.cachegrind_file = profile_file.with_suffix('.cachegrind')
        self.script_file = self.profile_file.with_suffix('.py')
        self.profiled_app = ProfileMiddleware(
            app,
            log_filename=profile_file,
            discard_first_request=False,
            cachegrind_filename=self.cachegrind_file,
        )

    def _create_dump_script(self):
        if not self.script_file.exists():
            with self.script_file.open("w", encoding="utf-8") as f:
                f.write("#!/usr/bin/env python3\n"
                        "import pstats\n"
                        f'stats = pstats.Stats("{self.profile_file}")\n'
                        "stats.sort_stats('time').print_stats()\n")
            self.script_file.chmod(0o755)
            cmk.utils.log.logger.info(f"Created profile dump script: {self.script_file}")

    def reset_profiler(self):
        self.profile_file.unlink(missing_ok=True)
        self.cachegrind_file.unlink(missing_ok=True)
        self.profiled_app.profiler = profile.Profile()

    def __call__(self, environ, start_response):
        if _profiling_enabled(environ):
            self._create_dump_script()
            if not self.accumulate:
                self.reset_profiler()
            app = self.profiled_app
        else:
            app = self.app

        return app(environ, start_response)


def _profiling_enabled(environ):
    if not cmk.gui.config.profile:
        return False

    if cmk.gui.config.profile == "enable_by_var":
        req = Request(environ)
        if '_profile' not in req.args:
            return False

    return True


__all__ = ['ProfileSwitcher']
