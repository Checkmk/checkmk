#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ATTENTION. Template file from which config builds host check.
# ATTENTION. Relative imports are strictly _forbidden_.

import sys
from contextlib import suppress

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
import cmk.utils.log
import cmk.utils.password_store
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.core.active_config_layout import RELATIVE_PATH_SECRETS, RELATIVE_PATH_TRUSTED_CAS
from cmk.base.core.nagios import HostCheckConfig
from cmk.base.modes.check_mk import run_checking
from cmk.ccc.config_path import detect_latest_config_path
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugin_backend import (
    extract_known_discovery_rulesets,
    load_selected_plugins,
)
from cmk.discover_plugins import PluginLocation
from cmk.fetchers import StoredSecrets
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils.paths import omd_root

# This will be replaced by the config generation, when the template is instantiated.
CONFIG = HostCheckConfig(
    delay_precompile=False,
    src="",
    dst="",
    verify_site_python=False,
    locations=[PluginLocation("dummy.callsite.of.plugin.location", "dummy_name")],
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
        # It's safe to resolve the latest link here, as the nagios core will not remove
        # serials while running checks.
        active_config_path = detect_latest_config_path(omd_root)

        _errors, sections, checks = config.load_and_convert_legacy_checks(CONFIG.checks_to_load)
        plugins = load_selected_plugins(CONFIG.locations, sections, checks, validate=debug)

        app = make_app(cmk_version.edition(omd_root))
        loading_result = config.load_packed_config(
            active_config_path,
            discovery_rulesets=extract_known_discovery_rulesets(plugins),
            get_builtin_host_labels=app.get_builtin_host_labels,
        )

        config.ipaddresses = CONFIG.ipaddresses
        config.ipv6addresses = CONFIG.ipv6addresses

        secrets = load_secrets_file(
            cmk.utils.password_store.active_secrets_path_site(
                RELATIVE_PATH_SECRETS, active_config_path
            )
        )

        return run_checking(
            app,
            loading_result.loaded_config,
            loading_result.config_cache.ruleset_matcher,
            loading_result.config_cache.label_manager,
            plugins,
            loading_result.config_cache,
            config.make_hosts_config(loading_result.loaded_config),
            # NOTE: At the time of writing we do respect the "monitoring_core" setting even in
            # the raw edition (which will fail if it is set to "cmc").
            # But here we are run by the Nagios core, so we can safely hardcode it.
            "nagios",
            config.ServiceDependsOn(
                tag_list=loading_result.config_cache.host_tags.tag_list,
                service_dependencies=loading_result.loaded_config.service_dependencies,
            ),
            {},
            [CONFIG.hostname],
            secrets_config_relay=StoredSecrets(
                path=cmk.utils.password_store.active_secrets_path_relay(), secrets=secrets
            ),
            secrets_config_site=StoredSecrets(
                path=cmk.utils.password_store.active_secrets_path_site(
                    RELATIVE_PATH_SECRETS, active_config_path
                ),
                secrets=secrets,
            ),
            trusted_ca_file=(active_config_path / RELATIVE_PATH_TRUSTED_CAS),
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
