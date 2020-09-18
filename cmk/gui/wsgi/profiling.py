# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pathlib
from typing import Optional

from werkzeug.wrappers import Request

from cmk.gui import config
import cmk.utils.paths
import cmk.utils.log

from repoze.profile import ProfileMiddleware  # type: ignore[import]


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

        self.profile_file = profile_file
        self.profiled_app = ProfileMiddleware(
            app,
            log_filename=profile_file,
            cachegrind_filename=profile_file.with_suffix(".cachegrind"),
        )

    def _create_dump_script(self):
        script_path = self.profile_file.with_suffix(".py")
        if not script_path.exists():
            with script_path.open("w", encoding="utf-8") as f:
                f.write("#!/usr/bin/env python3\n"
                        "import pstats\n"
                        f'stats = pstats.Stats("{self.profile_file}")\n'
                        "stats.sort_stats('time').print_stats()\n")
            script_path.chmod(0o755)
            cmk.utils.log.logger.info("Created profile dump script: %s", script_path)

    def __call__(self, environ, start_response):
        if _profiling_enabled(environ):
            self._create_dump_script()
            app = self.profiled_app
        else:
            app = self.app

        return app(environ, start_response)


def _profiling_enabled(environ):
    if not config.profile:
        return False

    if config.profile == "enable_by_var":
        req = Request(environ)
        if '_profile' not in req.args:
            return False

    return True


__all__ = ['ProfileSwitcher']
