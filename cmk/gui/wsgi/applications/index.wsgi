#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from wsgiref.types import WSGIEnvironment

from opentelemetry.instrumentation.wsgi import get_default_span_name, OpenTelemetryMiddleware

from cmk import trace
from cmk.ccc.site import get_omd_config, omd_site, resource_attributes_from_config
from cmk.ccc.version import edition
from cmk.gui.wsgi.applications.profile_switcher import (
    LazyImportProfilingMiddleware,
    ProfileConfigLoader,
    ProfileSetting,
)
from cmk.trace.export import exporter_from_config, init_span_processor
from cmk.utils import paths

DEBUG = False


def load_default_config() -> ProfileSetting:
    return ProfileSetting(
        mode="enable_by_var",
        cachegrind_file=paths.var_dir / "multisite.cachegrind",
        profile_file=paths.var_dir / "multisite.profile",
        accumulate=False,
        discard_first_request=False,
    )


def load_actual_config() -> ProfileSetting:
    """Load the profiling global setting from the Setup GUI config"""
    from cmk.gui import log, single_global_setting

    # Initialize logging as early as possible, before even importing most of the code.
    log.init_logging()
    log.set_log_levels(single_global_setting.load_gui_log_levels())

    # NOTE: Importing the module and not the function to enable mock-ability.
    return ProfileSetting(
        mode=single_global_setting.load_profiling_mode(),
        cachegrind_file=paths.var_dir / "multisite.cachegrind",
        profile_file=paths.var_dir / "multisite.profile",
        accumulate=False,
        discard_first_request=False,
    )


def _request_hook(span: trace.Span, environ: WSGIEnvironment) -> None:
    # Workaround for apache environment.  Same as in cmk.gui.http.Request.
    # Might be the wrong place to do this. Investigate...
    env = environ.copy()
    if "apache.version" in env and env.get("SCRIPT_NAME"):
        env["PATH_INFO"] = env["SCRIPT_NAME"]
    span.set_attribute("http.route", environ["PATH_INFO"])
    span.update_name(get_default_span_name(env))


init_span_processor(
    trace.init_tracing(
        service_namespace=trace.service_namespace_from_config(
            "", omd_config := get_omd_config(paths.omd_root)
        ),
        service_name="gui",
        service_instance_id=omd_site(),
        extra_resource_attributes=resource_attributes_from_config(paths.omd_root),
    ),
    exporter_from_config(
        exporter_log_level=logging.ERROR,
        config=trace.trace_send_config(omd_config),
    ),
)

Application = OpenTelemetryMiddleware(
    LazyImportProfilingMiddleware(
        app_factory_module="cmk.gui.wsgi.app",
        app_factory_name="make_wsgi_app",
        app_factory_args=(
            edition(paths.omd_root),
            DEBUG,
        ),
        app_factory_kwargs={},
        config_loader=ProfileConfigLoader(
            fetch_actual_config=load_actual_config,
            # first request needs to handle the config settings. This actually forces the import of most of cmk, which
            # should have been avoided. If this is needed, the logging setup part should be moved to a place where not
            # much else is imported.
            fetch_default_config=load_actual_config,
        ),
    ),
    request_hook=_request_hook,
)
