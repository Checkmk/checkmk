#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --check" command."""

from collections.abc import Mapping
from pathlib import Path

import cmk.ccc.debug
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.modes.check_mk import (
    CheckingOptions,
    fake_dns_address,
    FAKE_DNS_OPTION,
    FETCHER_OPTIONS,
    get_plugins_option,
    load_checks,
    option_detect_plugins,
    option_sections,
    run_checking,
    SNMP_BACKEND_OPTION,
    state_exit_code,
)
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.cli.engine.commands import option_names, option_string
from cmk.cli.internal import (
    Args,
    CLICommand,
    CLIOption,
    CommandContext,
    ExitCode,
    GlobalOptions,
    Options,
)
from cmk.server_side_calls_backend import load_secrets_file

# .
#   .--check---------------------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _checking_options(parsed: Mapping[str, object]) -> CheckingOptions:
    options = CheckingOptions()
    if "cache" in parsed:
        options["cache"] = True
    if "no-cache" in parsed:
        options["no-cache"] = True
    if "no-tcp" in parsed:
        options["no-tcp"] = True
    if "usewalk" in parsed:
        options["usewalk"] = True
    if "snmp-backend" in parsed:
        options["snmp-backend"] = option_string(parsed, "snmp-backend") or ""
    if "no-submit" in parsed:
        options["no-submit"] = True
    if "perfdata" in parsed:
        options["perfdata"] = True
    if "detect-sections" in parsed:
        options["detect-sections"] = option_names(parsed, "detect-sections", SectionName)
    if "plugins" in parsed:
        options["plugins"] = option_names(parsed, "plugins", CheckPluginName)
    if "detect-plugins" in parsed:
        options["detect-plugins"] = option_names(parsed, "detect-plugins", str)
    return options


def _mode_check(
    omd_root: Path, global_options: GlobalOptions, parsed: Options, args: Args
) -> ExitCode:
    app = make_app(omd_root)
    fake_dns = fake_dns_address(parsed)
    options = _checking_options(parsed)
    plugins = load_checks(debug=global_options.debug)
    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager

    secrets = load_secrets_file(cmk.utils.password_store.pending_secrets_path_site())

    state = run_checking(
        app,
        loaded_config,
        ruleset_matcher,
        label_manager,
        plugins,
        loading_result.config_cache,
        loading_result.hosts_config,
        loading_result.host_tags,
        loaded_config.monitoring_core,
        config.ServiceDependsOn(
            tag_list=loading_result.host_tags.tag_list,
            service_dependencies=loaded_config.service_dependencies,
            debug=global_options.debug,
        ),
        options,
        args,
        secrets_config_relay=AdHocSecrets(
            path=cmk.utils.password_store.generate_ad_hoc_secrets_path(
                cmk.utils.paths.relative_tmp_dir
            ),
            secrets=secrets,
        ),
        secrets_config_site=StoredSecrets(
            path=cmk.utils.password_store.pending_secrets_path_site(), secrets=secrets
        ),
        fake_dns=fake_dns,
        trusted_ca_file=cmk.utils.paths.trusted_ca_file,
        debug=global_options.debug,
    )
    return state_exit_code(state)


def _run_check(context: CommandContext, options: Options, args: Args) -> ExitCode:
    if context.global_options.debug:
        # the check engine and the crash reports read cmk.ccc.debug
        cmk.ccc.debug.enable()
    try:
        return _mode_check(context.omd_root, context.global_options, options, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return ExitCode.UNKNOWN


cli_command_check = CLICommand(
    long_option="check",
    handler_function=_run_check,
    argument=True,
    argument_descr="HOST [IPADDRESS]",
    argument_optional=True,
    sub_options=[
        *FETCHER_OPTIONS,
        SNMP_BACKEND_OPTION,
        CLIOption(
            long_option="no-submit",
            short_option="n",
            short_help="Do not submit results to core, do not save counters",
        ),
        CLIOption(
            long_option="perfdata",
            short_option="p",
            short_help="Also show performance data (use with -v)",
        ),
        option_sections,
        get_plugins_option(CheckPluginName),
        option_detect_plugins,
        FAKE_DNS_OPTION,
    ],
    short_help="Check all services on the given HOST",
    long_help=[
        (
            "Execute all checks on the given HOST. Optionally you can specify "
            "a second argument, the IPADDRESS. If you don't set this, the "
            "configured IP address of the HOST is used."
        ),
        (
            "By default the check results are sent to the core. If you provide "
            "the option '-n', the results will not be sent to the core and the "
            "counters of the check will not be stored."
        ),
        (
            "You can use '-v' to see the results of the checks. Add '-p' to "
            "also see the performance data of the checks. "
            "Can be restricted to certain check types. Write '--checks df -I' if "
            "you just want to look for new filesystems. Use 'check_mk -L' for a "
            "list of all check types. Use 'tcp' for all TCP based checks and "
            "'snmp' for all SNMP based checks."
        ),
    ],
)
