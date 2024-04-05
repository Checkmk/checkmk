#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import sys
from importlib import import_module

import cmk.utils.debug
import cmk.utils.log
from cmk.utils.config_path import LATEST_CONFIG
from cmk.utils.exceptions import MKTerminate
from cmk.utils.hostaddress import HostAddress, HostName

from cmk.checkengine.submitters import get_submitter

import cmk.base.check_api as check_api
import cmk.base.config as config
import cmk.base.obsolete_output as out
import cmk.base.utils
from cmk.base.api.agent_based.register import register_plugin_by_type

from cmk.discover_plugins import PluginLocation

from ._host_check_config import HostCheckConfig

# This will be replaced by the config genreration, when the template is instanciated.
CONFIG = HostCheckConfig(
    delay_precompile=False,
    src="",
    dst="",
    verify_site_python=False,
    locations=[PluginLocation("dummy.callsite.of.plugin.location")],
    checks_to_load=[],
    ipaddresses={HostName("somehost"): HostAddress("::")},
    ipv6addresses={},
    hostname=HostName("somehost"),
)


def main() -> int:
    # main() added for now to avoid executing code upon import (sys.path.pop !).
    # This function needs cleaning up, of course.

    if CONFIG.verify_site_python and not sys.executable.startswith("/omd"):
        sys.stdout.write("ERROR: Only executable with sites python\\n")
        return 2

    # Self-compile: replace symlink with precompiled python-code, if we are run for the first time
    if CONFIG.delay_precompile:
        import os

        if os.path.islink(CONFIG.dst):
            import py_compile

            os.remove(CONFIG.dst)
            py_compile.compile(CONFIG.src, CONFIG.dst, CONFIG.dst, True)
            os.chmod(CONFIG.dst, 0o700)

    for location in CONFIG.locations:
        module = import_module(location.module)
        if location.name is not None:
            register_plugin_by_type(location, getattr(module, location.name))

    # Register default Checkmk signal handler
    cmk.base.utils.register_sigint_handler()

    # initialize global variables
    # very simple commandline parsing: only -v (once or twice) and -d are supported

    cmk.utils.log.setup_console_logging()

    # TODO: This is not really good parsing, because it not cares about syntax like e.g. "-nv".
    #       The later regular argument parsing is handling this correctly. Try to clean this up.
    cmk.utils.log.logger.setLevel(
        cmk.utils.log.verbosity_to_log_level(len([a for a in sys.argv if a in ["-v", "--verbose"]]))
    )

    if "-d" in sys.argv:
        cmk.utils.debug.enable()

    config.load_checks(check_api.get_check_api_context, CONFIG.checks_to_load)

    config.load_packed_config(LATEST_CONFIG)

    config.ipaddresses = CONFIG.ipaddresses
    config.ipv6addresses = CONFIG.ipv6addresses

    try:
        # mode_check is `mode --check hostname`
        from cmk.base.modes.check_mk import mode_check

        return mode_check(
            get_submitter,
            {},
            [CONFIG.hostname],
            active_check_handler=lambda *args: None,
            keepalive=False,
        )
    except MKTerminate:
        out.output("<Interrupted>\n", stream=sys.stderr)
        return 1
    except SystemExit as e:
        return e.code  # type: ignore[return-value]  # what's the point of this anyway?
    except Exception as e:
        import traceback

        # status output message
        sys.stdout.write(
            f"UNKNOWN - Exception in precompiled check: {e} (details in long output)\n"
        )

        # generate traceback for long output
        sys.stdout.write(f"Traceback: {traceback.format_exc()}\n")
        return 3


if __name__ == "__main__":
    sys.exit(main())
