#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pathlib

from cmk.utils.profile_switcher import (
    LazyImportProfilingMiddleware,
    ProfileConfigLoader,
    ProfileSetting,
)

DEBUG = False


def load_default_config() -> ProfileSetting:
    # These local imports are intentional. As many imports as possible shall be
    # in scope of the import profiling middleware.
    from cmk.utils import paths

    return ProfileSetting(
        mode="enable_by_var",
        cachegrind_file=pathlib.Path(paths.var_dir) / "multisite.cachegrind",
        profile_file=pathlib.Path(paths.var_dir) / "multisite.profile",
        accumulate=False,
        discard_first_request=False,
    )


def load_actual_config() -> ProfileSetting:
    """Load the profiling global setting from the Setup GUI config"""
    # These local imports are intentional. As many imports as possible shall be
    # in scope of the import profiling middleware.
    from cmk.utils import paths

    from cmk.gui import log, single_global_setting

    # Initialize logging as early as possible, before even importing most of the code.
    log.init_logging()
    log.set_log_levels(single_global_setting.load_gui_log_levels())

    # NOTE: Importing the module and not the function to enable mock-ability.
    return ProfileSetting(
        mode=single_global_setting.load_profiling_mode(),
        cachegrind_file=pathlib.Path(paths.var_dir) / "multisite.cachegrind",
        profile_file=pathlib.Path(paths.var_dir) / "multisite.profile",
        accumulate=False,
        discard_first_request=False,
    )


Application = LazyImportProfilingMiddleware(
    app_factory_module="cmk.gui.wsgi.app",
    app_factory_name="make_wsgi_app",
    app_factory_args=(DEBUG,),
    app_factory_kwargs={},
    config_loader=ProfileConfigLoader(
        fetch_actual_config=load_actual_config,
        # first request needs to handle the config settings. This actually forces the import of most of cmk, which
        # should have been avoided. If this is needed, the logging setup part should be moved to a place where not
        # much else is imported.
        fetch_default_config=load_actual_config,
    ),
)
