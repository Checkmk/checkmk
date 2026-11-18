#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.checking import run_checking
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.plugins import CheckPluginName
from cmk.checkengine.specs.checkresults import ServiceState
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.check import (
    CheckingRequest,
    cli_command_check,
)
from cmk.server_side_calls_backend import load_secrets_file

from ._exit_code import state_exit_code
from ._file_cache import make_file_cache_options
from .agent_based import extract_plugin_selection, load_checks, PluginSelectionError


class _CheckHost(Protocol):
    def __call__(
        self, host: HostName, request: CheckingRequest, *, omd_root: Path, debug: bool
    ) -> ServiceState: ...


def _check_host(
    host: HostName, request: CheckingRequest, *, omd_root: Path, debug: bool
) -> ServiceState:
    app = make_app(omd_root)
    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
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

    return run_checking(
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
            debug=debug,
        ),
        [host] if request.address is None else [host, request.address],
        file_cache_options=make_file_cache_options(request.fetch.file_cache),
        snmp_backend=request.fetch.snmp_backend,
        usewalk=request.fetch.usewalk,
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
        fake_dns=request.fetch.fake_dns,
        debug=debug,
    )


@dataclass(frozen=True, kw_only=True)
class _CheckCommand:
    check_host: _CheckHost

    def run(self, context: CLIContext, request: CheckingRequest) -> CLIExitCode:
        assert request.host is not None
        try:
            return state_exit_code(
                self.check_host(
                    request.host,
                    request,
                    omd_root=context.omd_root,
                    debug=context.global_options.debug,
                )
            )
        except (PluginSelectionError, MKGeneralException) as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN


cli_handler_check = CLIHandler(
    command=cli_command_check, run=_CheckCommand(check_host=_check_host).run
)
