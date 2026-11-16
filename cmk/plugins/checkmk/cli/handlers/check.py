#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from pathlib import Path
from typing import Final

import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.checking import run_checking
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.plugins import CheckPluginName
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.check import (
    CheckingRequest,
    cli_command_check,
)
from cmk.plugins.checkmk.cli.options import make_file_cache_options
from cmk.server_side_calls_backend import load_secrets_file

from ._exit_code import state_exit_code
from .agent_based import extract_plugin_selection, load_checks

_HOST_AND_ADDRESS: Final = 2


def _mode_check(
    omd_root: Path, global_options: CLIGlobalOptions, request: CheckingRequest, args: CLIArgs
) -> CLIExitCode:
    if len(args) > _HOST_AND_ADDRESS:
        raise MKBailOut("Checking takes a HOST and an optional IPADDRESS, nothing more")
    app = make_app(omd_root)
    plugins = load_checks(debug=global_options.debug)
    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager

    secrets = load_secrets_file(cmk.utils.password_store.pending_secrets_path_site())

    selected_sections, run_plugin_names = extract_plugin_selection(
        detect_plugins=request.plugin_selection.detect_plugins,
        detect_sections=request.plugin_selection.detect_sections,
        selected_plugins=request.plugin_selection.plugins,
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
        file_cache_options=make_file_cache_options(request.file_cache),
        snmp_backend=request.snmp_backend,
        usewalk=request.usewalk,
        selected_sections=selected_sections,
        run_plugin_names=run_plugin_names,
        dry_run=request.no_submit,
        show_perfdata=request.perfdata,
        secrets_config_relay=AdHocSecrets(
            path=cmk.utils.password_store.generate_ad_hoc_secrets_path(
                cmk.utils.paths.relative_tmp_dir
            ),
            secrets=secrets,
        ),
        secrets_config_site=StoredSecrets(
            path=cmk.utils.password_store.pending_secrets_path_site(), secrets=secrets
        ),
        trusted_ca_file=cmk.utils.paths.trusted_ca_file,
        fake_dns=request.fake_dns,
        debug=global_options.debug,
    )
    return state_exit_code(state)


def _run_check(context: CLIContext, request: CheckingRequest, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_check(context.omd_root, context.global_options, request, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_handler_check = CLIHandler(command=cli_command_check, run=_run_check)
