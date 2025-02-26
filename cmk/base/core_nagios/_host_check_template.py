#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import sys
from contextlib import suppress

import cmk.ccc.debug

import cmk.utils.log
from cmk.utils.config_path import LATEST_CONFIG
from cmk.utils.hostaddress import HostAddress, HostName

import cmk.base.utils
from cmk.base import config
from cmk.base.api.agent_based.register import load_selected_plugins
from cmk.base.core_nagios import HostCheckConfig
from cmk.base.modes.check_mk import mode_check

from cmk.discover_plugins import PluginLocation

# This will be replaced by the config generation, when the template is instanciated.
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


def _self_compile(src: str, dst: str) -> None:
    """replace symlink with precompiled python-code, if we are run for the first time"""
    import os

    if not os.path.islink(dst):
        return

    import py_compile

    os.remove(dst)
    py_compile.compile(src, dst, dst, True)
    os.chmod(dst, 0o700)


def _simple_arg_parsing(executable: str, *opts: str) -> tuple[int, bool]:
    """Very basic argument parsing

    It seems this is all we needed in the last decade.

    >>> _simple_arg_parsing("/foo", "-vv", "-v", "-d")
    (3, True)
    """
    if not set(opts).issubset({"-v", "-vv", "-d"}):
        sys.stderr.write(f"usage: {executable} [-v | -vv] [-d]")
        raise SystemExit(3)

    j_opts = "".join(opts)
    return j_opts.count("v"), "d" in j_opts


def main() -> int:
    loglevel, debug = _simple_arg_parsing(*sys.argv)

    if CONFIG.verify_site_python and not sys.executable.startswith("/omd"):
        sys.stdout.write("ERROR: Only executable with sites python\\n")
        return 2

    if CONFIG.delay_precompile:
        _self_compile(CONFIG.src, CONFIG.dst)

    cmk.utils.log.setup_console_logging()

    cmk.utils.log.logger.setLevel(cmk.utils.log.verbosity_to_log_level(loglevel))
    if debug:
        cmk.ccc.debug.enable()

    try:
        _errors, sections, checks = config.load_and_convert_legacy_checks(CONFIG.checks_to_load)
        load_selected_plugins(CONFIG.locations, sections, checks, validate=debug)

        config.load_packed_config(LATEST_CONFIG)

        config.ipaddresses = CONFIG.ipaddresses
        config.ipv6addresses = CONFIG.ipv6addresses

        return mode_check(
            {},
            [CONFIG.hostname],
            active_check_handler=lambda *args: None,
            keepalive=False,
            precompiled_host_check=True,
        )
    except KeyboardInterrupt:
        with suppress(IOError):
            sys.stderr.write("<Interrupted>\n")
            sys.stderr.flush()
        return 1
    except Exception as e:
        import traceback

        sys.stdout.write(
            # status output message
            f"UNKNOWN - Exception in precompiled check: {e} (details in long output)\n"
            # generate traceback for long output
            f"Traceback: {traceback.format_exc()}\n"
        )
        return 3


if __name__ == "__main__":
    sys.exit(main())
