#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
import glob
import io
import logging
import operator
import os
import shlex
import shutil
import socket
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout, suppress
from itertools import islice
from pathlib import Path
from typing import Any, cast

import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.log as log
import cmk.utils.man_pages as man_pages
import cmk.utils.password_store
from cmk.utils.diagnostics import deserialize_cl_parameters, DiagnosticsCLParameters
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.exceptions import MKBailOut, MKGeneralException, MKSNMPError, OnError
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.paths import (
    autochecks_dir,
    counters_dir,
    data_source_cache_dir,
    discovered_host_labels_dir,
    local_agent_based_plugins_dir,
    local_checks_dir,
    logwatch_dir,
    nagios_startscript,
    omd_root,
    precompiled_hostchecks_dir,
    snmpwalks_dir,
    tcp_cache_dir,
    tmp_dir,
    var_dir,
)
from cmk.utils.type_defs import AgentRawData, CheckPluginName, CheckPluginNameStr
from cmk.utils.type_defs import DiscoveryResult as SingleHostDiscoveryResult
from cmk.utils.type_defs import HostAddress, HostName, ServiceDetails, ServiceState

from cmk.automations.results import (
    ActiveCheckResult,
    AnalyseHostResult,
    AnalyseServiceResult,
    CreateDiagnosticsDumpResult,
    DeleteHostsKnownRemoteResult,
    DeleteHostsResult,
    DiagHostResult,
    DiscoveredHostLabelsDict,
    GetAgentOutputResult,
    GetCheckInformationResult,
    GetConfigurationResult,
    GetSectionInformationResult,
    GetServicesLabelsResult,
    NotificationAnalyseResult,
    NotificationGetBulksResult,
    NotificationReplayResult,
    ReloadResult,
    RenameHostsResult,
    RestartResult,
    ScanParentsResult,
    ServiceDiscoveryPreviewResult,
    ServiceDiscoveryResult,
    ServiceInfo,
    SetAutochecksResult,
    SetAutochecksTable,
    SetAutochecksTablePre20,
    UpdateDNSCacheResult,
    UpdateHostLabelsResult,
)

import cmk.snmplib.snmp_modes as snmp_modes
import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import BackendOIDSpec, BackendSNMPTree, SNMPCredentials, SNMPHostConfig

from cmk.fetchers import FetcherType, get_raw_data, Mode, ProgramFetcher, TCPFetcher
from cmk.fetchers.filecache import FileCacheOptions, MaxAge
from cmk.fetchers.snmp import make_backend as make_snmp_backend

from cmk.checkers import parse_raw_data, plugin_contexts, SourceType
from cmk.checkers.discovery import AutocheckEntry, AutocheckServiceWithNodes
from cmk.checkers.summarize import summarize
from cmk.checkers.type_defs import NO_SELECTION

import cmk.base.agent_based.discovery as discovery
import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_api as check_api
import cmk.base.config as config
import cmk.base.core
import cmk.base.core_config as core_config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.nagios_utils
import cmk.base.notify as notify
import cmk.base.parent_scan
import cmk.base.sources as sources
from cmk.base.agent_based.confcheckers import (
    CheckPluginMapper,
    ConfiguredFetcher,
    ConfiguredParser,
    ConfiguredSummarizer,
    HostLabelPluginMapper,
    SectionPluginMapper,
)
from cmk.base.automations import Automation, automations, MKAutomationError
from cmk.base.config import ConfigCache, IgnoredServices
from cmk.base.core import CoreAction, do_restart
from cmk.base.core_factory import create_core
from cmk.base.diagnostics import DiagnosticsDump
from cmk.base.sources import make_parser

HistoryFile = str
HistoryFilePair = tuple[HistoryFile, HistoryFile]


class DiscoveryAutomation(Automation):
    def _trigger_discovery_check(self, config_cache: ConfigCache, host_name: HostName) -> None:
        """if required, schedule the "Check_MK Discovery" check"""
        if not config.inventory_check_autotrigger:
            return

        if config_cache.discovery_check_parameters(host_name).commandline_only:
            return

        if config_cache.is_cluster(host_name):
            return

        discovery.schedule_discovery_check(host_name)


def _extract_directive(directive: str, args: list[str]) -> tuple[bool, list[str]]:
    if directive in args:
        return True, [a for i, a in enumerate(args) if i != args.index(directive)]
    return False, args


class AutomationDiscovery(DiscoveryAutomation):
    cmd = "service-discovery"
    needs_config = True
    needs_checks = True

    # Does discovery for a list of hosts. Possible values for mode:
    # "new" - find only new services (like -I)
    # "remove" - remove exceeding services
    # "fixall" - find new, remove exceeding
    # "refresh" - drop all services and reinventorize
    # Hosts on the list that are offline (unmonitored) will
    # be skipped.
    def execute(self, args: list[str]) -> ServiceDiscoveryResult:
        force_snmp_cache_refresh, args = _extract_directive("@scan", args)
        _prevent_scan, args = _extract_directive("@noscan", args)
        raise_errors, args = _extract_directive("@raiseerrors", args)
        # Error sensitivity
        if raise_errors:
            on_error = OnError.RAISE
            os.dup2(os.open("/dev/null", os.O_WRONLY), 2)
        else:
            on_error = OnError.IGNORE

        # `force_snmp_cache_refresh` overrides `use_outdated` for SNMP.
        file_cache_options = FileCacheOptions(use_outdated=True)

        if len(args) < 2:
            raise MKAutomationError(
                "Need two arguments: new|remove|fixall|refresh|only-host-labels HOSTNAME"
            )

        mode = discovery.DiscoveryMode.from_str(args[0])
        hostnames = [HostName(h) for h in islice(args, 1, None)]

        config_cache = config.get_config_cache()

        results: dict[HostName, SingleHostDiscoveryResult] = {}

        parser = ConfiguredParser(
            config_cache,
            selected_sections=NO_SELECTION,
            keep_outdated=file_cache_options.keep_outdated,
            logger=logging.getLogger("cmk.base.discovery"),
        )
        fetcher = ConfiguredFetcher(
            config_cache,
            file_cache_options=file_cache_options,
            force_snmp_cache_refresh=force_snmp_cache_refresh,
            mode=Mode.DISCOVERY,
            on_error=on_error,
            selected_sections=NO_SELECTION,
            simulation_mode=config.simulation_mode,
        )
        for hostname in hostnames:
            results[hostname] = discovery.automation_discovery(
                hostname,
                config_cache=config_cache,
                parser=parser,
                fetcher=fetcher,
                summarizer=ConfiguredSummarizer(
                    config_cache,
                    hostname,
                    override_non_ok_state=None,
                ),
                section_plugins=SectionPluginMapper(),
                host_label_plugins=HostLabelPluginMapper(),
                check_plugins=CheckPluginMapper(),
                find_service_description=config.service_description,
                mode=mode,
                keep_clustered_vanished_services=True,
                service_filters=None,
                on_error=on_error,
            )

            if results[hostname].error_text is None:
                # Trigger the discovery service right after performing the discovery to
                # make the service reflect the new state as soon as possible.
                self._trigger_discovery_check(config_cache, hostname)

        discovery.rewrite_cluster_host_labels_file(config_cache, hostnames)

        return ServiceDiscoveryResult(results)


automations.register(AutomationDiscovery())


class AutomationDiscoveryPre22Name(AutomationDiscovery):
    cmd = "inventory"
    needs_config = True
    needs_checks = True


automations.register(AutomationDiscoveryPre22Name())


class AutomationDiscoveryPreview(Automation):
    cmd = "service-discovery-preview"
    needs_config = True
    needs_checks = True

    def execute(self, args: list[str]) -> ServiceDiscoveryPreviewResult:
        prevent_fetching, args = _extract_directive("@nofetch", args)
        raise_errors, args = _extract_directive("@raiseerrors", args)

        host_name = HostName(args[0])
        config_cache = config.get_config_cache()
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({host_name})
        return _get_discovery_preview(
            host_name, not prevent_fetching, OnError.RAISE if raise_errors else OnError.WARN
        )


automations.register(AutomationDiscoveryPreview())


class AutomationTryDiscovery(Automation):
    cmd = "try-inventory"  # TODO: drop with 2.3
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: list[str]) -> ServiceDiscoveryPreviewResult:
        # Note: in the @noscan case we *must not* fetch live data (it must be fast)
        # In the @scan case we *must* fetch live data (it must be up to date)
        _do_scan, args = _extract_directive("@scan", args)
        prevent_scan, args = _extract_directive("@noscan", args)
        raise_errors, args = _extract_directive("@raiseerrors", args)
        perform_scan = (
            not prevent_scan
        )  # ... or are you *absolutely* sure we always use *exactly* one of the directives :-)

        return _get_discovery_preview(
            HostName(args[0]), perform_scan, OnError.RAISE if raise_errors else OnError.WARN
        )


automations.register(AutomationTryDiscovery())


# TODO: invert the 'perform_scan' logic -> 'prevent_fetching'
def _get_discovery_preview(
    host_name: HostName, perform_scan: bool, on_error: OnError
) -> ServiceDiscoveryPreviewResult:
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        log.setup_console_logging()

        check_preview = _execute_discovery(host_name, perform_scan, on_error)

        def make_discovered_host_labels(
            labels: Sequence[HostLabel],
        ) -> DiscoveredHostLabelsDict:
            # this dict deduplicates label names! TODO: sort only if and where needed!
            return {l.name: l.to_dict() for l in sorted(labels, key=operator.attrgetter("name"))}

        changed_labels = make_discovered_host_labels(
            [
                l
                for l in check_preview.labels.vanished
                if l.name in make_discovered_host_labels(check_preview.labels.new)
            ]
        )

        return ServiceDiscoveryPreviewResult(
            output=buf.getvalue(),
            check_table=check_preview.table,
            host_labels=make_discovered_host_labels(check_preview.labels.present),
            new_labels=make_discovered_host_labels(
                [l for l in check_preview.labels.new if l.name not in changed_labels]
            ),
            vanished_labels=make_discovered_host_labels(
                [l for l in check_preview.labels.vanished if l.name not in changed_labels]
            ),
            changed_labels=changed_labels,
            source_results={
                k: (r.state, r.as_text()) for k, r in check_preview.source_results.items()
            },
            labels_by_host=check_preview.kept_labels,
        )


def _execute_discovery(
    host_name: HostName,
    perform_scan: bool,
    on_error: OnError,
) -> discovery.CheckPreview:
    file_cache_options = FileCacheOptions(
        use_outdated=not perform_scan, use_only_cache=not perform_scan
    )

    config_cache = config.get_config_cache()
    parser = ConfiguredParser(
        config_cache,
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("cmk.base.discovery"),
    )
    fetcher = ConfiguredFetcher(
        config_cache,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=perform_scan,
        mode=Mode.DISCOVERY,
        on_error=on_error,
        selected_sections=NO_SELECTION,
        simulation_mode=config.simulation_mode,
    )
    return discovery.get_check_preview(
        host_name,
        config_cache=config_cache,
        parser=parser,
        fetcher=fetcher,
        summarizer=ConfiguredSummarizer(
            config_cache,
            host_name,
            override_non_ok_state=None,
        ),
        section_plugins=SectionPluginMapper(),
        host_label_plugins=HostLabelPluginMapper(),
        check_plugins=CheckPluginMapper(),
        find_service_description=config.service_description,
        ignored_services=IgnoredServices(config_cache, host_name),
        on_error=on_error,
    )


class AutomationSetAutochecks(DiscoveryAutomation):
    cmd = "set-autochecks"
    needs_config = True
    needs_checks = False

    # Set the new list of autochecks. This list is specified by a
    # table of (checktype, item). No parameters are specified. Those
    # are either (1) kept from existing autochecks or (2) computed
    # from a new inventory.
    def execute(self, args: list[str]) -> SetAutochecksResult:
        hostname = HostName(args[0])
        new_items: SetAutochecksTable | SetAutochecksTablePre20 = ast.literal_eval(sys.stdin.read())

        config_cache = config.get_config_cache()

        # Not loading all checks improves performance of the calls and as a result the
        # responsiveness of the "service discovery" page.  For real hosts we don't need the checks,
        # because we already have calculated service descriptions. For clusters we have to load all
        # checks for config_cache.set_autochecks, because it needs to calculate the
        # service_descriptions of existing services to decided whether or not they are clustered
        # (See autochecks.set_autochecks_of_cluster())
        if config_cache.is_cluster(hostname):
            config.load_all_agent_based_plugins(
                check_api.get_check_api_context,
            )

        # Fix data from version <2.0
        new_services: list[AutocheckServiceWithNodes] = []
        for (raw_check_plugin_name, item), (
            _descr,
            params,
            raw_service_labels,
            found_on_nodes,
        ) in _transform_pre_20_items(new_items).items():
            check_plugin_name = CheckPluginName(raw_check_plugin_name)

            new_services.append(
                AutocheckServiceWithNodes(
                    AutocheckEntry(check_plugin_name, item, params, raw_service_labels),
                    found_on_nodes,
                )
            )

        config_cache.set_autochecks(hostname, new_services)
        self._trigger_discovery_check(config_cache, hostname)
        return SetAutochecksResult()


def _transform_pre_20_items(
    new_items: SetAutochecksTablePre20 | SetAutochecksTable,
) -> SetAutochecksTable:
    if _is_20_set_autochecks_format(new_items):
        return cast(SetAutochecksTable, new_items)

    fixed_items: SetAutochecksTable = {}
    for (check_type, item), (data_container, service_labels) in cast(
        SetAutochecksTablePre20, new_items
    ).items():
        fixed_items[(check_type, item)] = (
            data_container["service_description"],
            data_container["params"],
            service_labels,
            data_container["found_on_nodes"],
        )
    return fixed_items


def _is_20_set_autochecks_format(new_items: SetAutochecksTablePre20 | SetAutochecksTable) -> bool:
    # try-inventory in 2.0 generates a different data format if it detects that the remote version
    # is too old (<2.0). It reports a shorter tuple. The paramstring gets repurposed and
    # acts as generic data container.
    for _key, value in new_items.items():
        return len(value) > 2
    return True


automations.register(AutomationSetAutochecks())


class AutomationUpdateHostLabels(DiscoveryAutomation):
    """Set the new collection of discovered host labels"""

    cmd = "update-host-labels"
    needs_config = True
    needs_checks = False

    def execute(self, args: list[str]) -> UpdateHostLabelsResult:
        hostname = HostName(args[0])
        new_host_labels = ast.literal_eval(sys.stdin.read())
        DiscoveredHostLabelsStore(hostname).save(new_host_labels)

        config_cache = config.get_config_cache()
        self._trigger_discovery_check(config_cache, hostname)
        return UpdateHostLabelsResult()


automations.register(AutomationUpdateHostLabels())


class AutomationRenameHosts(Automation):
    cmd = "rename-hosts"
    needs_config = True
    needs_checks = True

    def __init__(self) -> None:
        super().__init__()
        self._finished_history_files: dict[HistoryFilePair, list[HistoryFile]] = {}

    # WATO calls this automation when hosts have been renamed. We need to change
    # several file and directory names. This function has no argument but reads
    # Python pair-list from stdin:
    # [("old1", "new1"), ("old2", "new2")])
    def execute(self, args: list[str]) -> RenameHostsResult:
        renamings: list[HistoryFilePair] = ast.literal_eval(sys.stdin.read())

        actions: list[str] = []

        # The history archive can be renamed with running core. We need to keep
        # the list of already handled history archive files, because a new history
        # file may be created by the core during this step. All unhandled files,
        # including the current history files will be handled later when the core
        # is stopped.
        for oldname, newname in renamings:
            self._finished_history_files[
                (oldname, newname)
            ] = self._rename_host_in_core_history_archive(oldname, newname)
            if self._finished_history_files[(oldname, newname)]:
                actions.append("history")

        # At this place WATO already has changed it's configuration. All further
        # data might be changed by the still running core. So we need to stop
        # it now.
        core_was_running = self._core_is_running()
        if core_was_running:
            cmk.base.core.do_core_action(
                CoreAction.STOP,
                quiet=True,
                monitoring_core=config.monitoring_core,
            )

        try:
            for oldname, newname in renamings:
                actions += self._rename_host_files(oldname, newname)
        finally:
            # Start monitoring again
            if core_was_running:
                # force config generation to succeed. The core *must* start.
                # TODO: Can't we drop this hack since we have config warnings now?
                config.ignore_ip_lookup_failures()
                # In this case the configuration is already locked by the caller of the automation.
                # If that is on the local site, we can not lock the configuration again during baking!
                # (If we are on a remote site now, locking *would* work, but we will not bake agents anyway.)
                _execute_silently(CoreAction.START, skip_config_locking_for_bakery=True)

                for hostname in config.failed_ip_lookups():
                    actions.append("dnsfail-" + hostname)

        # Convert actions into a dictionary { "what" : count }
        action_counts: dict[str, int] = {}
        for action in actions:
            action_counts.setdefault(action, 0)
            action_counts[action] += 1

        return RenameHostsResult(action_counts)

    def _core_is_running(self) -> bool:
        if config.monitoring_core == "nagios":
            command = nagios_startscript + " status"
        else:
            command = "omd status cmc"
        return (
            subprocess.call(
                shlex.split(command),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            == 0
        )

    def _rename_host_files(  # pylint: disable=too-many-branches
        self,
        oldname: HistoryFile,
        newname: HistoryFile,
    ) -> list[str]:
        actions = []

        if self._rename_host_file(autochecks_dir, oldname + ".mk", newname + ".mk"):
            actions.append("autochecks")

        if self._rename_host_file(
            str(discovered_host_labels_dir), oldname + ".mk", newname + ".mk"
        ):
            actions.append("host-labels")

        # Rename temporary files of the host
        for d in ["cache", "counters"]:
            if self._rename_host_file(str(tmp_dir / d), oldname, newname):
                actions.append(d)

        if self._rename_host_dir(str(tmp_dir / "piggyback"), oldname, newname):
            actions.append("piggyback-load")

        # Rename piggy files *created* by the host
        piggybase = str(tmp_dir) + "/piggyback/"
        if os.path.exists(piggybase):
            for piggydir in os.listdir(piggybase):
                if self._rename_host_file(piggybase + piggydir, oldname, newname):
                    actions.append("piggyback-pig")

        # Logwatch
        if self._rename_host_dir(logwatch_dir, oldname, newname):
            actions.append("logwatch")

        # SNMP walks
        if self._rename_host_file(snmpwalks_dir, oldname, newname):
            actions.append("snmpwalk")

        # HW/SW-Inventory
        if self._rename_host_file(var_dir + "/inventory", oldname, newname):
            self._rename_host_file(var_dir + "/inventory", oldname + ".gz", newname + ".gz")
            actions.append("inv")

        if self._rename_host_dir(var_dir + "/inventory_archive", oldname, newname):
            actions.append("invarch")

        # Baked agents
        baked_agents_dir = var_dir + "/agents/"
        have_renamed_agent = False
        if os.path.exists(baked_agents_dir):
            for opsys in os.listdir(baked_agents_dir):
                if self._rename_host_file(baked_agents_dir + opsys, oldname, newname):
                    have_renamed_agent = True
        if have_renamed_agent:
            actions.append("agent")

        # Agent deployment
        deployment_dir = var_dir + "/agent_deployment/"
        if self._rename_host_file(deployment_dir, oldname, newname):
            actions.append("agent_deployment")

        actions += self._omd_rename_host(oldname, newname)

        return actions

    def _rename_host_dir(self, basedir: str, oldname: str, newname: str) -> int:
        if os.path.exists(basedir + "/" + oldname):
            if os.path.exists(basedir + "/" + newname):
                shutil.rmtree(basedir + "/" + newname)
            os.rename(basedir + "/" + oldname, basedir + "/" + newname)
            return 1
        return 0

    def _rename_host_file(self, basedir: str, oldname: str, newname: str) -> int:
        if os.path.exists(basedir + "/" + oldname):
            if os.path.exists(basedir + "/" + newname):
                os.remove(basedir + "/" + newname)
            os.rename(basedir + "/" + oldname, basedir + "/" + newname)
            return 1
        return 0

    # This functions could be moved out of Checkmk.
    def _omd_rename_host(  # pylint: disable=too-many-branches
        self,
        oldname: str,
        newname: str,
    ) -> list[str]:
        oldregex = self._escape_name_for_regex_matching(oldname)
        actions = []

        # Temporarily stop processing of performance data
        npcd_running = (omd_root / "tmp/pnp4nagios/run/npcd.pid").exists()
        if npcd_running:
            os.system("omd stop npcd >/dev/null 2>&1 </dev/null")

        rrdcache_running = (omd_root / "tmp/run/rrdcached.sock").exists()
        if rrdcache_running:
            os.system("omd stop rrdcached >/dev/null 2>&1 </dev/null")

        try:
            # Fix pathnames in XML files
            self.rename_host_in_files(
                str(omd_root / "var/pnp4nagios/perfdata" / oldname / "*.xml"),
                "/perfdata/%s/" % oldregex,
                "/perfdata/%s/" % newname,
            )

            # RRD files
            if self._rename_host_dir(str(omd_root / "var/pnp4nagios/perfdata"), oldname, newname):
                actions.append("rrd")

            # RRD files
            if self._rename_host_dir(str(omd_root / "var/check_mk/rrd"), oldname, newname):
                actions.append("rrd")

            # entries of rrdcached journal
            if self.rename_host_in_files(
                str(omd_root / "var/rrdcached/rrd.journal.*"),
                "/(perfdata|rrd)/%s/" % oldregex,
                "/\\1/%s/" % newname,
                extended_regex=True,
            ):
                actions.append("rrdcached")

            # Spoolfiles of NPCD
            if self.rename_host_in_files(  #
                "%s/var/pnp4nagios/perfdata.dump" % omd_root,
                "HOSTNAME::%s    " % oldregex,  #
                "HOSTNAME::%s    " % newname,
            ) or self.rename_host_in_files(  #
                "%s/var/pnp4nagios/spool/perfdata.*" % omd_root,
                "HOSTNAME::%s    " % oldregex,  #
                "HOSTNAME::%s    " % newname,
            ):
                actions.append("pnpspool")
        finally:
            if rrdcache_running:
                os.system("omd start rrdcached >/dev/null 2>&1 </dev/null")

            if npcd_running:
                os.system("omd start npcd >/dev/null 2>&1 </dev/null")

        self._rename_host_in_remaining_core_history_files(oldname, newname)

        # State retention (important for Downtimes, Acknowledgements, etc.)
        if config.monitoring_core == "nagios":
            if self.rename_host_in_files(
                "%s/var/nagios/retention.dat" % omd_root,
                "^host_name=%s$" % oldregex,
                "host_name=%s" % newname,
                extended_regex=True,
            ):
                actions.append("retention")

        else:  # CMC
            # Create a file "renamed_hosts" with the information about the
            # renaming of the hosts. The core will honor this file when it
            # reads the status file with the saved state.
            Path(var_dir, "core/renamed_hosts").write_text(f"{oldname}\n{newname}\n")
            actions.append("retention")

        # NagVis maps
        if self.rename_host_in_files(
            "%s/etc/nagvis/maps/*.cfg" % omd_root,
            "^[[:space:]]*host_name=%s[[:space:]]*$" % oldregex,
            "host_name=%s" % newname,
            extended_regex=True,
        ):
            actions.append("nagvis")

        return actions

    def _rename_host_in_remaining_core_history_files(self, oldname: str, newname: str) -> list[str]:
        """Perform the rename operation in all history archive files that have not been handled yet"""
        finished_file_paths = self._finished_history_files[(oldname, newname)]
        all_file_paths = set(self._get_core_history_files(only_archive=False))
        todo_file_paths = list(all_file_paths.difference(finished_file_paths))
        return self._rename_host_in_core_history_files(todo_file_paths, oldname, newname)

    def _rename_host_in_core_history_archive(self, oldname: str, newname: str) -> list[str]:
        """Perform the rename operation in all history archive files"""
        file_paths = self._get_core_history_files(only_archive=True)
        return self._rename_host_in_core_history_files(file_paths, oldname, newname)

    def _get_core_history_files(self, only_archive: bool) -> list[str]:
        path_patterns = [
            "var/check_mk/core/archive/*",
            "var/nagios/archive/*",
        ]

        if not only_archive:
            path_patterns += [
                "var/check_mk/core/history",
                "var/nagios/nagios.log",
            ]

        file_paths: list[str] = []
        for path_pattern in path_patterns:
            file_paths += glob.glob(f"{omd_root}/{path_pattern}")
        return file_paths

    def _rename_host_in_core_history_files(
        self, file_paths: list[str], oldname: str, newname: str
    ) -> list[str]:
        oldregex = self._escape_name_for_regex_matching(oldname)

        # Logfiles and history files of CMC and Nagios. Problem
        # here: the exact place of the hostname varies between the
        # various log entry lines
        sed_commands = r"""
s/(INITIAL|CURRENT) (HOST|SERVICE) STATE: {old};/\1 \2 STATE: {new};/
s/(HOST|SERVICE) (DOWNTIME |FLAPPING |)ALERT: {old};/\1 \2ALERT: {new};/
s/PASSIVE (HOST|SERVICE) CHECK: {old};/PASSIVE \1 CHECK: {new};/
s/(HOST|SERVICE) NOTIFICATION: ([^;]+);{old};/\1 NOTIFICATION: \2;{new};/
""".format(
            old=oldregex,
            new=newname,
        )

        handled_files: list[str] = []

        subprocess.run(
            ["sed", "-ri", "--file=/dev/fd/0", *file_paths],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            close_fds=True,
            input=sed_commands.encode("utf-8"),
            check=False,
        )
        # TODO: error handling?

        handled_files += file_paths

        return handled_files

    # Returns True in case files were found, otherwise False
    def rename_host_in_files(
        self, path_pattern: str, old: str, new: str, extended_regex: bool = False
    ) -> bool:
        paths = glob.glob(path_pattern)
        if paths:
            extended = ["-r"] if extended_regex else []
            subprocess.call(
                ["sed", "-i"] + extended + [f"s@{old}@{new}@"] + paths,
                stderr=subprocess.DEVNULL,
            )
            return True

        return False

    def _escape_name_for_regex_matching(self, name: str) -> str:
        return name.replace(".", "[.]")


automations.register(AutomationRenameHosts())


class AutomationGetServicesLabels(Automation):
    cmd = "get-services-labels"
    needs_config = True
    needs_checks = True

    def execute(self, args: list[str]) -> GetServicesLabelsResult:
        host_name, services = HostName(args[0]), args[1:]
        ruleset_matcher = config.get_config_cache().ruleset_matcher
        config_cache = config.get_config_cache()
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({host_name})
        return GetServicesLabelsResult(
            {service: ruleset_matcher.labels_of_service(host_name, service) for service in services}
        )


automations.register(AutomationGetServicesLabels())


class AutomationAnalyseServices(Automation):
    cmd = "analyse-service"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: list[str]) -> AnalyseServiceResult:
        host_name = HostName(args[0])
        servicedesc = args[1]
        config_cache = config.get_config_cache()
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({host_name})
        return (
            AnalyseServiceResult(
                service_info=service_info,
                labels=config_cache.ruleset_matcher.labels_of_service(host_name, servicedesc),
                label_sources=config_cache.ruleset_matcher.label_sources_of_service(
                    host_name, servicedesc
                ),
            )
            if (
                service_info := self._get_service_info(
                    config_cache=config_cache,
                    host_name=host_name,
                    host_attrs=config_cache.get_host_attributes(host_name),
                    servicedesc=servicedesc,
                )
            )
            else AnalyseServiceResult(
                service_info={},
                labels={},
                label_sources={},
            )
        )

    # Determine the type of the check, and how the parameters are being
    # constructed
    # TODO: Refactor this huge function
    def _get_service_info(
        self,
        config_cache: ConfigCache,
        host_name: HostName,
        host_attrs: config.ObjectAttributes,
        servicedesc: str,
    ) -> ServiceInfo:
        # We just consider types of checks that are managed via WATO.
        # We have the following possible types of services:
        # 1. enforced services (currently overriding discovered services)
        # 2. disocvered services
        # 3. classical checks
        # 4. active checks

        # 1. Enforced services
        for checkgroup_name, service in config_cache.enforced_services_table(host_name).values():
            if service.description == servicedesc:
                return {
                    "origin": "static",  # TODO: (how) can we change this to "enforced"?
                    "checkgroup": checkgroup_name,
                    "checktype": str(service.check_plugin_name),
                    "item": service.item,
                    "parameters": service.parameters.preview(cmk.base.core.timeperiod_active),
                }

        # 2. Load all autochecks of the host in question and try to find
        # our service there
        if (
            autocheck_service := self._get_service_info_from_autochecks(
                config_cache, host_name, servicedesc
            )
        ) is not None:
            return autocheck_service

        # 3. Classical checks
        for entry in config_cache.custom_checks(host_name):
            desc = entry["service_description"]
            if desc == servicedesc:
                result: ServiceInfo = {
                    "origin": "classic",
                }
                if "command_line" in entry:  # Only active checks have a command line
                    result["command_line"] = entry["command_line"]
                return result

        # 4. Active checks
        with plugin_contexts.current_host(host_name):
            for plugin_name, entries in config_cache.active_checks(host_name):
                for active_check_params in entries:
                    for description in core_config.get_active_check_descriptions(
                        host_name,
                        config_cache.alias(host_name),
                        host_attrs,
                        plugin_name,
                        active_check_params,
                    ):
                        if description == servicedesc:
                            return {
                                "origin": "active",
                                "checktype": plugin_name,
                                "parameters": active_check_params,
                            }

        return {}  # not found

    @staticmethod
    def _get_service_info_from_autochecks(
        config_cache: ConfigCache, host_name: HostName, servicedesc: str
    ) -> ServiceInfo | None:
        # TODO: There is a lot of duplicated logic with discovery.py/check_table.py. Clean this
        # whole function up.
        # NOTE: Iterating over the check table would make things easier. But we might end up with
        # differen information. Also: check table forgets wether it's an *auto*check.
        table = config_cache.check_table(host_name)
        services = (
            [
                service
                for node in config_cache.nodes_of(host_name) or []
                for service in config_cache.get_autochecks_of(node)
                if host_name == config_cache.host_of_clustered_service(node, service.description)
            ]
            if config_cache.is_cluster(host_name)
            else config_cache.get_autochecks_of(host_name)
        )

        for service in services:

            if service.id() not in table:
                continue  # this is a clustered service

            if service.description != servicedesc:
                continue

            plugin = agent_based_register.get_check_plugin(service.check_plugin_name)
            if plugin is None:
                # plugin can only be None if we looked for the "Unimplemented check..." description.
                # In this case we can run into the 'not found' case below.
                continue

            return {
                "origin": "auto",
                "checktype": str(plugin.name),
                "checkgroup": str(plugin.check_ruleset_name),
                "item": service.item,
                "inv_parameters": service.discovered_parameters,
                "factory_settings": plugin.check_default_parameters,
                # effective parameters:
                "parameters": service.parameters.preview(cmk.base.core.timeperiod_active),
            }

        return None


automations.register(AutomationAnalyseServices())


class AutomationAnalyseHost(Automation):
    cmd = "analyse-host"
    needs_config = True
    needs_checks = False

    def execute(self, args: list[str]) -> AnalyseHostResult:
        host_name = HostName(args[0])
        config_cache = config.get_config_cache()
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({host_name})
        return AnalyseHostResult(
            config_cache.labels(host_name),
            config_cache.label_sources(host_name),
        )


automations.register(AutomationAnalyseHost())


class ABCDeleteHosts:
    needs_config = False
    needs_checks = False

    def _execute(self, args: list[str]) -> None:
        for hostname_str in args:
            self._delete_host_files(HostName(hostname_str))

    @abc.abstractmethod
    def _single_file_paths(self, hostname: HostName) -> Iterable[str]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _delete_host_files(self, hostname: HostName) -> None:
        raise NotImplementedError()

    def _delete_datasource_dirs(self, hostname: HostName) -> None:
        try:
            ds_directories = os.listdir(data_source_cache_dir)
        except FileNotFoundError:
            ds_directories = []

        for data_source_name in ds_directories:
            filename = f"{data_source_cache_dir}/{data_source_name}/{hostname}"
            self._delete_if_exists(filename)

    def _delete_baked_agents(self, hostname: HostName) -> None:
        # softlinks for baked agents. obsolete packages are removed upon next bake action
        # TODO: Move to bakery code
        baked_agents_dir = var_dir + "/agents/"
        if os.path.exists(baked_agents_dir):
            for folder in os.listdir(baked_agents_dir):
                self._delete_if_exists(f"{folder}/{hostname}")

    def _delete_logwatch(self, hostname: HostName) -> None:
        with suppress(FileNotFoundError):
            shutil.rmtree(f"{logwatch_dir}/{hostname}")

    def _delete_if_exists(self, path: str) -> None:
        """Delete the given file or folder in case it exists"""
        try:
            os.unlink(path)
        except IsADirectoryError:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass


class AutomationDeleteHosts(ABCDeleteHosts, Automation):
    cmd = "delete-hosts"

    def execute(self, args: list[str]) -> DeleteHostsResult:
        self._execute(args)
        return DeleteHostsResult()

    def _single_file_paths(self, hostname: HostName) -> list[str]:
        return [
            f"{precompiled_hostchecks_dir}/{hostname}",
            f"{precompiled_hostchecks_dir}/{hostname}.py",
            f"{autochecks_dir}/{hostname}.mk",
            f"{counters_dir}/{hostname}",
            f"{tcp_cache_dir}/{hostname}",
            f"{var_dir}/persisted/{hostname}",
            f"{var_dir}/inventory/{hostname}",
            f"{var_dir}/inventory/{hostname}.gz",
            f"{var_dir}/agent_deployment/{hostname}",
        ]

    def _delete_host_files(self, hostname: HostName) -> None:
        """
        The inventory_archive as well as the performance data is kept
        we do not want to loose any historic data for accidentally deleted hosts.

        These files are cleaned up by the disk space mechanism.
        """
        if hostname in (".", ".."):
            return

        for path in self._single_file_paths(hostname):
            self._delete_if_exists(path)

        self._delete_datasource_dirs(hostname)
        self._delete_baked_agents(hostname)
        self._delete_logwatch(hostname)


automations.register(AutomationDeleteHosts())


class AutomationDeleteHostsKnownRemote(ABCDeleteHosts, Automation):
    """Cleanup automation call for hosts that were previously located on the
    local site and are now handled by a remote site"""

    cmd = "delete-hosts-known-remote"

    def execute(self, args: list[str]) -> DeleteHostsKnownRemoteResult:
        self._execute(args)
        return DeleteHostsKnownRemoteResult()

    def _single_file_paths(self, hostname: HostName) -> list[str]:
        return [
            f"{precompiled_hostchecks_dir}/{hostname}",
            f"{precompiled_hostchecks_dir}/{hostname}.py",
            f"{autochecks_dir}/{hostname}.mk",
            f"{counters_dir}/{hostname}",
            f"{tcp_cache_dir}/{hostname}",
            f"{var_dir}/persisted/{hostname}",
        ]

    def _delete_host_files(self, hostname: HostName) -> None:
        """
        The following locations are skipped on local sites for hosts only known
        on remote sites:
        - var/check_mk/agent_deployment
        - var/check_mk/agents
        """
        for path in self._single_file_paths(hostname):
            self._delete_if_exists(path)

        self._delete_datasource_dirs(hostname)
        self._delete_logwatch(hostname)


automations.register(AutomationDeleteHostsKnownRemote())


class AutomationRestart(Automation):
    cmd = "restart"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def _mode(self) -> CoreAction:
        if config.monitoring_core == "cmc" and not self._check_plugins_have_changed():
            return CoreAction.RELOAD
        return CoreAction.RESTART

    def execute(self, args: list[str]) -> RestartResult:
        return _execute_silently(self._mode(), None if not args else set(args))

    def _check_plugins_have_changed(self) -> bool:
        last_time = self._time_of_last_core_restart()
        for checks_path in [
            local_checks_dir,
            local_agent_based_plugins_dir,
        ]:
            if not checks_path.exists():
                continue
            this_time = self._last_modification_in_dir(checks_path)
            if this_time > last_time:
                return True
        return False

    def _last_modification_in_dir(self, dir_path: Path) -> float:
        max_time = os.stat(dir_path).st_mtime
        for file_name in os.listdir(dir_path):
            max_time = max(max_time, os.stat(str(dir_path) + "/" + file_name).st_mtime)
        return max_time

    def _time_of_last_core_restart(self) -> float:
        if config.monitoring_core == "cmc":
            pidfile_path = omd_root / "tmp/run/cmc.pid"
        else:
            pidfile_path = omd_root / "tmp/lock/nagios.lock"

        try:
            return pidfile_path.stat().st_mtime
        except FileNotFoundError:
            return 0.0


automations.register(AutomationRestart())


class AutomationReload(AutomationRestart):
    cmd = "reload"

    def _mode(self) -> CoreAction:
        if self._check_plugins_have_changed():
            return CoreAction.RESTART
        return CoreAction.RELOAD

    def execute(self, args: list[str]) -> ReloadResult:
        return ReloadResult(super().execute(args).config_warnings)


automations.register(AutomationReload())


def _execute_silently(
    action: CoreAction,
    hosts_to_update: set[str] | None = None,
    skip_config_locking_for_bakery: bool = False,
) -> RestartResult:
    with redirect_stdout(open(os.devnull, "w")):
        log.setup_console_logging()
        try:
            do_restart(
                create_core(config.monitoring_core),
                action,
                hosts_to_update=hosts_to_update,
                locking_mode=config.restart_locking,
                duplicates=config.duplicate_hosts(),
                skip_config_locking_for_bakery=skip_config_locking_for_bakery,
            )
        except (MKBailOut, MKGeneralException) as e:
            raise MKAutomationError(str(e))

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKAutomationError(str(e))

        return RestartResult(config_warnings.get_configuration())


class AutomationGetConfiguration(Automation):
    cmd = "get-configuration"
    needs_config = False
    # This needed the checks in the past. This was necessary to get the
    # default values of check related global settings. This kind of
    # global settings have been removed from the global settings page
    # of WATO. We can now disable this (by default).
    # We need to be careful here, because users may have added their own
    # global settings related to checks. To deal with this, we check
    # for requested but missing global variables and load the checks in
    # case one is missing. When it's still missing then, we silenlty skip
    # this option (like before).
    needs_checks = False

    def execute(self, args: list[str]) -> GetConfigurationResult:
        config.load(with_conf_d=False)

        # We read the list of variable names from stdin since
        # that could be too much for the command line
        variable_names = ast.literal_eval(sys.stdin.read())

        missing_variables = [v for v in variable_names if not hasattr(config, v)]

        if missing_variables:
            config.load_all_agent_based_plugins(
                check_api.get_check_api_context,
            )
            config.load(with_conf_d=False)

        result = {}
        for varname in variable_names:
            if hasattr(config, varname):
                value = getattr(config, varname)
                if not hasattr(value, "__call__"):
                    result[varname] = value
        return GetConfigurationResult(result)


automations.register(AutomationGetConfiguration())


class AutomationGetCheckInformation(Automation):
    cmd = "get-check-information"
    needs_config = False
    needs_checks = True

    def execute(self, args: list[str]) -> GetCheckInformationResult:
        manuals = man_pages.all_man_pages()

        plugin_infos: dict[CheckPluginNameStr, dict[str, Any]] = {}
        for plugin in agent_based_register.iter_all_check_plugins():
            plugin_info = plugin_infos.setdefault(
                str(plugin.name),
                {
                    "title": self._get_title(manuals, plugin.name),
                    "name": str(plugin.name),
                    "service_description": str(plugin.service_name),
                },
            )
            if plugin.check_ruleset_name:
                plugin_info["check_ruleset_name"] = str(plugin.check_ruleset_name)
                # TODO: kept for compatibility. See if we can drop this.
                plugin_info["group"] = str(plugin.check_ruleset_name)
            if plugin.discovery_ruleset_name:
                plugin_info["discovery_ruleset_name"] = str(plugin.discovery_ruleset_name)

        return GetCheckInformationResult(plugin_infos)

    @staticmethod
    def _get_title(manuals: Mapping[str, str], plugin_name: CheckPluginName) -> str:
        manfile = manuals.get(str(plugin_name))
        if manfile:
            try:
                return cmk.utils.man_pages.get_title_from_man_page(Path(manfile))
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                raise MKAutomationError(f"Failed to parse man page '{plugin_name}': {e}")
        return str(plugin_name)


automations.register(AutomationGetCheckInformation())


class AutomationGetSectionInformation(Automation):
    cmd = "get-section-information"
    needs_config = False
    needs_checks = True

    def execute(self, args: list[str]) -> GetSectionInformationResult:

        section_infos = {
            str(section.name): {
                # for now, we need only these two.
                "name": str(section.name),
                "type": "agent",
            }
            for section in agent_based_register.iter_all_agent_sections()
        }
        section_infos.update(
            {
                str(section.name): {
                    "name": str(section.name),
                    "type": "snmp",
                }
                for section in agent_based_register.iter_all_snmp_sections()
            }
        )
        return GetSectionInformationResult(section_infos)


automations.register(AutomationGetSectionInformation())


class AutomationScanParents(Automation):
    cmd = "scan-parents"
    needs_config = True
    needs_checks = True

    def execute(self, args: list[str]) -> ScanParentsResult:
        settings = {
            "timeout": int(args[0]),
            "probes": int(args[1]),
            "max_ttl": int(args[2]),
            "ping_probes": int(args[3]),
        }
        hostnames = [HostName(hn) for hn in islice(args, 4, None)]
        if not cmk.base.parent_scan.traceroute_available():
            raise MKAutomationError("Cannot find binary <tt>traceroute</tt> in search path.")
        config_cache = config.get_config_cache()

        try:
            gateways = cmk.base.parent_scan.scan_parents_of(
                config_cache, hostnames, silent=True, settings=settings
            )
            return ScanParentsResult(gateways)
        except Exception as e:
            raise MKAutomationError("%s" % e)


automations.register(AutomationScanParents())


class AutomationDiagHost(Automation):
    cmd = "diag-host"
    needs_config = True
    needs_checks = True

    def execute(  # pylint: disable=too-many-branches
        self,
        args: list[str],
    ) -> DiagHostResult:
        host_name = HostName(args[0])
        test, ipaddress, snmp_community = args[1:4]
        agent_port, snmp_timeout, snmp_retries = map(int, args[4:7])

        config_cache = config.get_config_cache()
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({host_name})

        # In 1.5 the tcp connect timeout has been added. The automation may
        # be called from a remote site with an older version. For this reason
        # we need to deal with the old args.
        if len(args) == 14:
            tcp_connect_timeout = None
            cmd = args[7]
        else:
            tcp_connect_timeout = float(args[7])
            cmd = args[8]

        snmpv3_use = None
        snmpv3_auth_proto = None
        snmpv3_security_name = None
        snmpv3_security_password = None
        snmpv3_privacy_proto = None
        snmpv3_privacy_password = None

        if len(args) > 9:
            snmpv3_use = args[9]
            if snmpv3_use in ["authNoPriv", "authPriv"]:
                snmpv3_auth_proto, snmpv3_security_name, snmpv3_security_password = args[10:13]
            else:
                snmpv3_security_name = args[11]
            if snmpv3_use == "authPriv":
                snmpv3_privacy_proto, snmpv3_privacy_password = args[13:15]

        # No caching option over commandline here.
        file_cache_options = FileCacheOptions()

        if not ipaddress:
            try:
                resolved_address = config.lookup_ip_address(config_cache, host_name)
            except Exception:
                raise MKGeneralException("Cannot resolve hostname %s into IP address" % host_name)

            if resolved_address is None:
                raise MKGeneralException("Cannot resolve hostname %s into IP address" % host_name)

            ipaddress = resolved_address

        try:
            if test == "ping":
                return DiagHostResult(*self._execute_ping(config_cache, host_name, ipaddress))

            if test == "agent":
                return DiagHostResult(
                    *self._execute_agent(
                        config_cache,
                        host_name,
                        ipaddress,
                        agent_port=agent_port,
                        cmd=cmd,
                        tcp_connect_timeout=tcp_connect_timeout,
                        file_cache_options=file_cache_options,
                    )
                )

            if test == "traceroute":
                return DiagHostResult(*self._execute_traceroute(config_cache, host_name, ipaddress))

            if test.startswith("snmp"):
                if config.simulation_mode:
                    raise MKSNMPError(
                        "Simulation mode enabled. Not trying to contact snmp datasource"
                    )
                return DiagHostResult(
                    *self._execute_snmp(
                        test,
                        config_cache.make_snmp_config(host_name, ipaddress, SourceType.HOST),
                        host_name,
                        ipaddress,
                        snmp_community,
                        snmp_timeout,
                        snmp_retries,
                        snmpv3_use,
                        snmpv3_auth_proto,
                        snmpv3_security_name,
                        snmpv3_security_password,
                        snmpv3_privacy_proto,
                        snmpv3_privacy_password,
                    )
                )

            return DiagHostResult(
                1,
                "Command not implemented",
            )

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            return DiagHostResult(
                1,
                str(e),
            )

    def _execute_ping(
        self, config_cache: ConfigCache, hostname: HostName, ipaddress: str
    ) -> tuple[int, str]:
        base_cmd = (
            "ping6" if config_cache.default_address_family(hostname) is socket.AF_INET6 else "ping"
        )
        completed_process = subprocess.run(
            [base_cmd, "-A", "-i", "0.2", "-c", "2", "-W", "5", ipaddress],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )
        return completed_process.returncode, completed_process.stdout

    def _execute_agent(
        self,
        config_cache: ConfigCache,
        host_name: HostName,
        ipaddress: HostAddress,
        *,
        agent_port: int,
        cmd: str,
        tcp_connect_timeout: float | None,
        file_cache_options: FileCacheOptions,
    ) -> tuple[int, str]:
        check_interval = config_cache.check_mk_check_interval(host_name)
        state, output = 0, ""
        for source in sources.make_sources(
            host_name,
            ipaddress,
            ConfigCache.address_family(host_name),
            config_cache=config_cache,
            simulation_mode=config.simulation_mode,
            file_cache_options=file_cache_options,
            file_cache_max_age=MaxAge(
                checking=config.check_max_cachefile_age,
                discovery=1.5 * check_interval,
                inventory=1.5 * check_interval,
            ),
        ):
            source_info = source.source_info()
            if source_info.fetcher_type is FetcherType.SNMP:
                continue

            fetcher = source.fetcher()
            if source_info.fetcher_type is FetcherType.PROGRAM and cmd:
                assert isinstance(fetcher, ProgramFetcher)
                fetcher = ProgramFetcher(
                    cmdline=config_cache.translate_commandline(host_name, ipaddress, cmd),
                    stdin=fetcher.stdin,
                    is_cmc=fetcher.is_cmc,
                )
            elif source_info.fetcher_type is FetcherType.TCP:
                assert isinstance(fetcher, TCPFetcher)
                port = agent_port or fetcher.address[1]
                timeout = tcp_connect_timeout or fetcher.timeout
                fetcher = TCPFetcher(
                    family=fetcher.family,
                    address=(fetcher.address[0], port),
                    timeout=timeout,
                    host_name=fetcher.host_name,
                    encryption_handling=fetcher.encryption_handling,
                    pre_shared_secret=fetcher.pre_shared_secret,
                )

            raw_data = get_raw_data(
                source.file_cache(
                    simulation=config.simulation_mode,
                    file_cache_options=file_cache_options,
                ),
                fetcher,
                Mode.CHECKING,
            )
            if raw_data.is_ok():
                # We really receive a byte string here. The agent sections
                # may have different encodings and are normally decoded one
                # by one (AgentChecker._parse_host_section).  For the
                # moment we use UTF-8 with fallback to latin-1 by default,
                # similar to the AgentChecker, but we do not
                # respect the ecoding options of sections.
                # If this is a problem, we would have to apply parse and
                # decode logic and unparse the decoded output again.
                output += ensure_str_with_fallback(
                    raw_data.ok,
                    encoding="utf-8",
                    fallback="latin-1",
                )
            else:
                state = 1
                output += str(raw_data.error)

        return state, output

    def _execute_traceroute(
        self, config_cache: ConfigCache, hostname: HostName, ipaddress: str
    ) -> tuple[int, str]:
        family_flag = (
            "-6" if config_cache.default_address_family(hostname) is socket.AF_INET6 else "-4"
        )
        try:
            completed_process = subprocess.run(
                ["traceroute", family_flag, "-n", ipaddress],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                check=False,
            )
        except FileNotFoundError:
            return 1, "Cannot find binary <tt>traceroute</tt>."
        return completed_process.returncode, completed_process.stdout

    def _execute_snmp(  # type: ignore[no-untyped-def]  # pylint: disable=too-many-branches
        self,
        test: str,
        snmp_config: SNMPHostConfig,
        hostname: HostName,
        ipaddress: HostAddress,
        snmp_community,
        snmp_timeout,
        snmp_retries,
        snmpv3_use,
        snmpv3_auth_proto,
        snmpv3_security_name,
        snmpv3_security_password,
        snmpv3_privacy_proto,
        snmpv3_privacy_password,
    ) -> tuple[int, str]:
        # SNMPv3 tuples
        # ('noAuthNoPriv', "username")
        # ('authNoPriv', 'md5', '11111111', '22222222')
        # ('authPriv', 'md5', '11111111', '22222222', 'DES', '33333333')

        credentials: SNMPCredentials = snmp_config.credentials

        # Insert preconfigured communitiy
        if test == "snmpv3":
            if snmpv3_use:
                snmpv3_credentials = [snmpv3_use]
                if snmpv3_use in ["authNoPriv", "authPriv"]:
                    if (
                        not isinstance(snmpv3_auth_proto, str)
                        or not isinstance(snmpv3_security_name, str)
                        or not isinstance(snmpv3_security_password, str)
                    ):
                        raise TypeError()
                    snmpv3_credentials.extend(
                        [snmpv3_auth_proto, snmpv3_security_name, snmpv3_security_password]
                    )
                else:
                    if not isinstance(snmpv3_security_name, str):
                        raise TypeError()
                    snmpv3_credentials.extend([snmpv3_security_name])

                if snmpv3_use == "authPriv":
                    if not isinstance(snmpv3_privacy_proto, str) or not isinstance(
                        snmpv3_privacy_password, str
                    ):
                        raise TypeError()
                    snmpv3_credentials.extend([snmpv3_privacy_proto, snmpv3_privacy_password])

                credentials = tuple(snmpv3_credentials)
        elif snmp_community:
            credentials = snmp_community

        # Determine SNMPv2/v3 community
        if hostname not in config.explicit_snmp_communities:
            config_cache = config.get_config_cache()
            cred = config_cache.snmp_credentials_of_version(
                hostname, snmp_version=3 if test == "snmpv3" else 2
            )
            if cred is not None:
                credentials = cred

        # SNMP versions
        if test in ["snmpv2", "snmpv3"]:
            is_bulkwalk_host = True
            is_snmpv2or3_without_bulkwalk_host = False
        elif test == "snmpv2_nobulk":
            is_bulkwalk_host = False
            is_snmpv2or3_without_bulkwalk_host = True
        elif test == "snmpv1":
            is_bulkwalk_host = False
            is_snmpv2or3_without_bulkwalk_host = False

        else:
            return 1, "SNMP command not implemented"

        # TODO: What about SNMP management boards?
        # TODO: `snmp_table.get_snmp_table()` with some cache handling
        #       is what the SNMPFetcher already does.  Work on reducing
        #       code duplication.
        snmp_config = SNMPHostConfig(
            is_ipv6_primary=snmp_config.is_ipv6_primary,
            hostname=hostname,
            ipaddress=ipaddress,
            credentials=credentials,
            port=snmp_config.port,
            is_bulkwalk_host=is_bulkwalk_host,
            is_snmpv2or3_without_bulkwalk_host=is_snmpv2or3_without_bulkwalk_host,
            bulk_walk_size_of=snmp_config.bulk_walk_size_of,
            timing={
                "timeout": snmp_timeout,
                "retries": snmp_retries,
            },
            oid_range_limits=snmp_config.oid_range_limits,
            snmpv3_contexts=snmp_config.snmpv3_contexts,
            character_encoding=snmp_config.character_encoding,
            snmp_backend=snmp_config.snmp_backend,
        )

        data = snmp_table.get_snmp_table(
            section_name=None,
            tree=BackendSNMPTree(
                base=".1.3.6.1.2.1.1",
                oids=[BackendOIDSpec(c, "string", False) for c in "1456"],
            ),
            walk_cache={},
            backend=make_snmp_backend(snmp_config, log.logger),
        )

        if data:
            return 0, "sysDescr:\t%s\nsysContact:\t%s\nsysName:\t%s\nsysLocation:\t%s\n" % tuple(
                data[0]
            )

        return 1, "Got empty SNMP response"


automations.register(AutomationDiagHost())


class AutomationActiveCheck(Automation):
    cmd = "active-check"
    needs_config = True
    needs_checks = True

    def execute(self, args: list[str]) -> ActiveCheckResult:
        host_name = HostName(args[0])
        plugin, item = args[1:]

        config_cache = config.get_config_cache()
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({host_name})
        with redirect_stdout(open(os.devnull, "w")):
            host_attrs = config_cache.get_host_attributes(host_name)

        if plugin == "custom":
            for entry in config_cache.custom_checks(host_name):
                if entry["service_description"] != item:
                    continue

                command_line = self._replace_macros(
                    host_name, entry["service_description"], entry.get("command_line", "")
                )
                if command_line:
                    cmd = core_config.autodetect_plugin(command_line)
                    return ActiveCheckResult(*self._execute_check_plugin(cmd))

                return ActiveCheckResult(
                    -1,
                    "Passive check - cannot be executed",
                )

        try:
            act_info = config.active_check_info[plugin]
        except KeyError:
            return ActiveCheckResult(
                None,
                "Failed to compute check result",
            )

        # Set host name for host_name()-function (part of the Check API)
        # (used e.g. by check_http)
        stored_passwords = cmk.utils.password_store.load()
        with plugin_contexts.current_host(host_name):
            for params in dict(config_cache.active_checks(host_name)).get(plugin, []):

                for description, command_args in core_config.iter_active_check_services(
                    plugin, act_info, host_name, host_attrs, params, stored_passwords
                ):
                    if description != item:
                        continue

                    command_line = self._replace_macros(
                        host_name,
                        description,
                        act_info["command_line"].replace("$ARG1$", command_args),
                    )
                    cmd = core_config.autodetect_plugin(command_line)
                    return ActiveCheckResult(*self._execute_check_plugin(cmd))

        return ActiveCheckResult(
            None,
            "Failed to compute check result",
        )

    def _load_resource_file(self, macros: dict[str, str]) -> None:
        try:
            for line in (omd_root / "etc/nagios/resource.cfg").open():
                line = line.strip()
                if not line or line[0] == "#":
                    continue
                varname, value = line.split("=", 1)
                macros[varname] = value
        except Exception:
            if cmk.utils.debug.enabled():
                raise

    # Simulate replacing some of the more important macros of host and service. We
    # cannot use dynamic macros, of course. Note: this will not work
    # without OMD, since we do not know the value of $USER1$ and $USER2$
    # here. We could read the Nagios resource.cfg file, but we do not
    # know for sure the place of that either.
    def _replace_macros(self, hostname: HostName, service_desc: str, commandline: str) -> str:
        config_cache = config.get_config_cache()
        macros = ConfigCache.get_host_macros_from_attributes(
            hostname, config_cache.get_host_attributes(hostname)
        )
        service_attrs = core_config.get_service_attributes(hostname, service_desc, config_cache)
        macros.update(ConfigCache.get_service_macros_from_attributes(service_attrs))
        self._load_resource_file(macros)

        return replace_macros_in_str(commandline, {k: f"{v}" for k, v in macros.items()})

    def _execute_check_plugin(self, commandline: str) -> tuple[ServiceState, ServiceDetails]:
        try:
            result = subprocess.run(
                shlex.split(commandline),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            status = result.returncode if result.returncode in [0, 1, 2] else 3
            output = result.stdout.strip().decode().split("|", 1)[0]  # Drop performance data

            return status, output

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            return 3, "UNKNOWN - Cannot execute command: %s" % e


automations.register(AutomationActiveCheck())


class AutomationUpdateDNSCache(Automation):
    cmd = "update-dns-cache"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: list[str]) -> UpdateDNSCacheResult:
        config_cache = config.get_config_cache()
        return UpdateDNSCacheResult(
            *ip_lookup.update_dns_cache(
                ip_lookup_configs=(
                    config_cache.ip_lookup_config(hn) for hn in config_cache.all_active_hosts()
                ),
                configured_ipv4_addresses=config.ipaddresses,
                configured_ipv6_addresses=config.ipv6addresses,
                simulation_mode=config.simulation_mode,
                override_dns=config.fake_dns,
            )
        )


automations.register(AutomationUpdateDNSCache())


class AutomationGetAgentOutput(Automation):
    cmd = "get-agent-output"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: list[str]) -> GetAgentOutputResult:
        hostname = HostName(args[0])
        ty = args[1]
        config_cache = config.get_config_cache()

        # No caching option over commandline here.
        file_cache_options = FileCacheOptions()

        success = True
        output = ""
        info = b""

        try:
            ipaddress = config.lookup_ip_address(config_cache, hostname)
            check_interval = config_cache.check_mk_check_interval(hostname)
            if ty == "agent":
                for source in sources.make_sources(
                    hostname,
                    ipaddress,
                    ConfigCache.address_family(hostname),
                    config_cache=config.get_config_cache(),
                    simulation_mode=config.simulation_mode,
                    file_cache_options=file_cache_options,
                    file_cache_max_age=MaxAge(
                        checking=config.check_max_cachefile_age,
                        discovery=1.5 * check_interval,
                        inventory=1.5 * check_interval,
                    ),
                ):
                    source_info = source.source_info()
                    if source_info.fetcher_type is FetcherType.SNMP:
                        continue

                    raw_data = get_raw_data(
                        source.file_cache(
                            simulation=config.simulation_mode, file_cache_options=file_cache_options
                        ),
                        source.fetcher(),
                        Mode.CHECKING,
                    )
                    host_sections = parse_raw_data(
                        make_parser(
                            config_cache,
                            source_info,
                            checking_sections=config_cache.make_checking_sections(
                                hostname, selected_sections=NO_SELECTION
                            ),
                            keep_outdated=file_cache_options.keep_outdated,
                            logger=logging.getLogger("cmk.base.checking"),
                        ),
                        raw_data,
                        selection=NO_SELECTION,
                    )
                    source_results = summarize(
                        hostname,
                        ipaddress,
                        host_sections,
                        exit_spec=config_cache.exit_code_spec(hostname, source_info.ident),
                        time_settings=config_cache.get_piggybacked_hosts_time_settings(
                            piggybacked_hostname=hostname,
                        ),
                        is_piggyback=config_cache.is_piggyback_host(hostname),
                        fetcher_type=source_info.fetcher_type,
                    )
                    if any(r.state != 0 for r in source_results):
                        # Optionally show errors of problematic data sources
                        success = False
                        output += f"[{source_info.ident}] {', '.join(r.summary for r in source_results)}\n"
                    assert raw_data.ok is not None
                    info += raw_data.ok
            else:
                if not ipaddress:
                    raise MKGeneralException("Failed to gather IP address of %s" % hostname)
                snmp_config = config_cache.make_snmp_config(hostname, ipaddress, SourceType.HOST)
                backend = make_snmp_backend(snmp_config, log.logger, use_cache=False)

                lines = []
                for walk_oid in snmp_modes.oids_to_walk():
                    try:
                        for oid, value in snmp_modes.walk_for_export(walk_oid, backend=backend):
                            raw_oid_value = f"{oid} {value}\n"
                            lines.append(raw_oid_value.encode())
                    except Exception as e:
                        if cmk.utils.debug.enabled():
                            raise
                        success = False
                        output += f"OID '{oid}': {e}\n"

                info = b"".join(lines)
        except Exception as e:
            success = False
            output = f"Failed to fetch data from {hostname}: {e}\n"
            if cmk.utils.debug.enabled():
                raise

        return GetAgentOutputResult(
            success,
            output,
            AgentRawData(info),
        )


automations.register(AutomationGetAgentOutput())


class AutomationNotificationReplay(Automation):
    cmd = "notification-replay"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: list[str]) -> NotificationReplayResult:
        nr = args[0]
        notify.notification_replay_backlog(int(nr))
        return NotificationReplayResult()


automations.register(AutomationNotificationReplay())


class AutomationNotificationAnalyse(Automation):
    cmd = "notification-analyse"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: list[str]) -> NotificationAnalyseResult:
        nr = args[0]
        return NotificationAnalyseResult(notify.notification_analyse_backlog(int(nr)))


automations.register(AutomationNotificationAnalyse())


class AutomationGetBulks(Automation):
    cmd = "notification-get-bulks"
    needs_config = False
    needs_checks = False

    def execute(self, args: list[str]) -> NotificationGetBulksResult:
        only_ripe = args[0] == "1"
        return NotificationGetBulksResult(notify.find_bulks(only_ripe))


automations.register(AutomationGetBulks())


class AutomationCreateDiagnosticsDump(Automation):
    cmd = "create-diagnostics-dump"
    needs_config = False
    needs_checks = False

    def execute(self, args: DiagnosticsCLParameters) -> CreateDiagnosticsDumpResult:
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            log.setup_console_logging()
            dump = DiagnosticsDump(deserialize_cl_parameters(args))
            dump.create()
            return CreateDiagnosticsDumpResult(
                output=buf.getvalue(),
                tarfile_path=str(dump.tarfile_path),
                tarfile_created=dump.tarfile_created,
            )


automations.register(AutomationCreateDiagnosticsDump())
