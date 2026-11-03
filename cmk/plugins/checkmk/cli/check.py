#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --check" command."""

import itertools
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, TypedDict

import cmk.ccc.debug
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.checking import run_checking
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.cli.engine.commands import option_names, option_string
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Option as CLIOption
from cmk.cli.internal import Options
from cmk.server_side_calls_backend import load_secrets_file

from .agent_based import extract_plugin_selection, load_checks
from .exit_code import state_exit_code
from .options import (
    fake_dns_address,
    FAKE_DNS_OPTION,
    FETCHER_OPTIONS,
    get_plugins_option,
    handle_fetcher_options,
    option_detect_plugins,
    option_sections,
    parse_snmp_backend,
    SNMP_BACKEND_OPTION,
)

# .
#   .--check---------------------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


CheckingOptions = TypedDict(
    "CheckingOptions",
    {
        "cache": Literal[True],
        "snmp-backend": str,
        "no-cache": Literal[True],
        "no-tcp": Literal[True],
        "usewalk": Literal[True],
        "no-submit": bool,
        "perfdata": bool,
        "detect-sections": frozenset[SectionName],
        "plugins": frozenset[CheckPluginName],
        "detect-plugins": frozenset[str],
    },
    total=False,
)


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
    omd_root: Path, global_options: CLIGlobalOptions, parsed: Options, args: CLIArgs
) -> CLIExitCode:
    app = make_app(omd_root)
    fake_dns = fake_dns_address(parsed)
    options = _checking_options(parsed)
    plugins = load_checks(debug=global_options.debug)
    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager

    secrets = load_secrets_file(cmk.utils.password_store.pending_secrets_path_site())

    try:
        snmp_backend = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc
    selected_sections, run_plugin_names = extract_plugin_selection(
        detect_plugins=options.get("detect-plugins"),
        detect_sections=options.get("detect-sections"),
        selected_plugins=options.get("plugins"),
        plugins=plugins.check_plugins,
        sections=itertools.chain(plugins.agent_sections.values(), plugins.snmp_sections.values()),
        type_=CheckPluginName,
    )

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
        args,
        file_cache_options=handle_fetcher_options(options),
        snmp_backend=snmp_backend,
        usewalk=bool(options.get("usewalk", False)),
        selected_sections=selected_sections,
        run_plugin_names=run_plugin_names,
        dry_run=options.get("no-submit", False),
        show_perfdata=options.get("perfdata", False),
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


def _run_check(context: CLIContext, options: Options, args: CLIArgs) -> CLIExitCode:
    if context.global_options.debug:
        # the store reads cmk.ccc.debug
        cmk.ccc.debug.enable()
    try:
        return _mode_check(context.omd_root, context.global_options, options, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_command_check = CLICommand(
    name="check",
    long="check",
    handler_function=_run_check,
    arguments=CLIArguments("HOST [IPADDRESS]", optional=True),
    sub_options=[
        *FETCHER_OPTIONS,
        SNMP_BACKEND_OPTION,
        CLIOption(
            long="no-submit",
            short="n",
            help="Do not submit results to core, do not save counters",
        ),
        CLIOption(
            long="perfdata",
            short="p",
            help="Also show performance data (use with -v)",
        ),
        option_sections,
        get_plugins_option(CheckPluginName),
        option_detect_plugins,
        FAKE_DNS_OPTION,
    ],
    help="Check all services on the given HOST",
    description=[
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
