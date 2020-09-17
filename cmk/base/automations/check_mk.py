#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import errno
import glob
import io
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import redirect_stdout, redirect_stderr

from six import ensure_binary, ensure_str

import cmk.utils.debug
import cmk.utils.log as log
import cmk.utils.man_pages as man_pages
import cmk.utils.paths
from cmk.utils.check_utils import maincheckify
from cmk.utils.diagnostics import deserialize_cl_parameters, DiagnosticsCLParameters
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.exceptions import MKGeneralException, MKBailOut
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    HostAddress,
    HostName,
    ServiceDetails,
    ServiceState,
)

import cmk.snmplib.snmp_modes as snmp_modes
import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import SNMPCredentials, SNMPHostConfig, SNMPTree

from cmk.fetchers import factory

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_api as check_api
import cmk.base.check_api_utils as check_api_utils
import cmk.base.check_table as check_table
import cmk.base.check_utils
import cmk.base.checking
import cmk.base.config as config
import cmk.base.core
from cmk.base.core import CoreAction, do_restart
import cmk.base.core_config as core_config
import cmk.base.checkers as checkers
import cmk.base.discovery as discovery
import cmk.base.ip_lookup as ip_lookup
import cmk.base.nagios_utils
import cmk.base.notify as notify
import cmk.base.parent_scan

from cmk.base.automations import Automation, automations, MKAutomationError
from cmk.base.core_factory import create_core
from cmk.base.diagnostics import DiagnosticsDump
from cmk.base.discovered_labels import DiscoveredHostLabels, DiscoveredServiceLabels, ServiceLabel

HistoryFile = str
HistoryFilePair = Tuple[HistoryFile, HistoryFile]


class DiscoveryAutomation(Automation):
    def _trigger_discovery_check(self, config_cache: config.ConfigCache,
                                 host_config: config.HostConfig) -> None:
        """if required, schedule the "Check_MK Discovery" check"""
        if not config.inventory_check_autotrigger:
            return

        service_discovery_name = config_cache.service_discovery_name()
        disc_check_params = host_config.discovery_check_parameters
        if not host_config.add_service_discovery_check(disc_check_params, service_discovery_name):
            return

        if host_config.is_cluster:
            return

        discovery.schedule_discovery_check(host_config.hostname)


def _set_cache_opts_of_checkers(use_caches: bool) -> None:
    # TODO check these settings vs.
    # cmk/base/checkers/_abstract.py:set_cache_opts
    if use_caches:
        checkers.FileCacheFactory.use_outdated = True
        # TODO why does this only apply to TCP data sources and not
        # to all agent data sources?
        checkers.tcp.TCPSource.use_only_cache = True
    checkers.FileCacheFactory.maybe = use_caches


class AutomationDiscovery(DiscoveryAutomation):
    cmd = "inventory"  # TODO: Rename!
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    # Does discovery for a list of hosts. Possible values for mode:
    # "new" - find only new services (like -I)
    # "remove" - remove exceeding services
    # "fixall" - find new, remove exceeding
    # "refresh" - drop all services and reinventorize
    # Hosts on the list that are offline (unmonitored) will
    # be skipped.
    def execute(self, args: List[str]) -> Tuple[Dict[str, List[int]], Dict[HostName, str]]:
        # Error sensivity
        if args[0] == "@raiseerrors":
            args = args[1:]
            on_error = "raise"
            os.dup2(os.open("/dev/null", os.O_WRONLY), 2)
        else:
            on_error = "ignore"

        # Do a full service scan
        if args[0] == "@scan":
            args = args[1:]
            use_caches = False
        else:
            use_caches = True

        _set_cache_opts_of_checkers(use_caches)

        if len(args) < 2:
            raise MKAutomationError("Need two arguments: new|remove|fixall|refresh HOSTNAME")

        mode = args[0]
        hostnames = args[1:]
        service_filters = discovery.get_service_filter_funcs({})

        config_cache = config.get_config_cache()

        counts = {}
        failed_hosts = {}

        for hostname in hostnames:
            host_config = config_cache.get_host_config(hostname)
            result, error = discovery.discover_on_host(
                config_cache,
                host_config,
                mode,
                use_caches,
                service_filters,
                on_error=on_error,
            )
            counts[hostname] = [
                result["self_new"],
                result["self_removed"],
                result["self_kept"],
                result["self_total"],
                result["self_new_host_labels"],
                result["self_total_host_labels"],
            ]

            if error is not None:
                failed_hosts[hostname] = error
            else:
                self._trigger_discovery_check(config_cache, host_config)

        return counts, failed_hosts


automations.register(AutomationDiscovery())


class AutomationTryDiscovery(Automation):
    cmd = "try-inventory"  # TODO: Rename!
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: List[str]) -> Dict[str, Any]:
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            log.setup_console_logging()
            log.logger.setLevel(log.VERBOSE)
            check_preview_table, host_labels = self._execute_discovery(args)
            return {
                "output": buf.getvalue(),
                "check_table": check_preview_table,
                "host_labels": host_labels.to_dict(),
            }

    def _execute_discovery(
            self, args: List[str]) -> Tuple[discovery.CheckPreviewTable, DiscoveredHostLabels]:

        use_caches = False
        if args[0] == '@noscan':
            args = args[1:]
            use_caches = True

        elif args[0] == '@scan':
            # Do a full service scan
            args = args[1:]

        _set_cache_opts_of_checkers(use_caches)

        if args[0] == '@raiseerrors':
            on_error = "raise"
            args = args[1:]
        else:
            on_error = "warn"

        hostname = args[0]
        return discovery.get_check_preview(
            hostname,
            use_caches=use_caches,
            on_error=on_error,
        )


automations.register(AutomationTryDiscovery())


class AutomationSetAutochecks(DiscoveryAutomation):
    cmd = "set-autochecks"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    # Set the new list of autochecks. This list is specified by a
    # table of (checktype, item). No parameters are specified. Those
    # are either (1) kept from existing autochecks or (2) computed
    # from a new inventory.
    def execute(self, args: List[str]) -> None:
        hostname = args[0]
        new_items = ast.literal_eval(sys.stdin.read())

        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        new_services = []
        for (check_plugin_name, item), (params, raw_service_labels) in new_items.items():
            check_plugin_name = CheckPluginName(check_plugin_name)

            descr = config.service_description(hostname, check_plugin_name, item)

            service_labels = DiscoveredServiceLabels()
            for label_id, label_value in raw_service_labels.items():
                service_labels.add_label(ServiceLabel(label_id, label_value))

            new_services.append(
                discovery.Service(check_plugin_name, item, descr, params, service_labels))

        host_config.set_autochecks(new_services)
        self._trigger_discovery_check(config_cache, host_config)


automations.register(AutomationSetAutochecks())


class AutomationUpdateHostLabels(DiscoveryAutomation):
    """Set the new collection of discovered host labels"""
    cmd = "update-host-labels"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: List[str]) -> None:
        hostname = args[0]
        new_host_labels = ast.literal_eval(sys.stdin.read())
        DiscoveredHostLabelsStore(hostname).save(new_host_labels)

        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)
        self._trigger_discovery_check(config_cache, host_config)


automations.register(AutomationUpdateHostLabels())


class AutomationRenameHosts(Automation):
    cmd = "rename-hosts"
    needs_config = True
    needs_checks = True

    def __init__(self) -> None:
        super(AutomationRenameHosts, self).__init__()
        self._finished_history_files: Dict[HistoryFilePair, List[HistoryFile]] = {}

    # WATO calls this automation when hosts have been renamed. We need to change
    # several file and directory names. This function has no argument but reads
    # Python pair-list from stdin:
    # [("old1", "new1"), ("old2", "new2")])
    def execute(self, args: List[str]) -> Dict[str, int]:
        renamings: List[HistoryFilePair] = ast.literal_eval(sys.stdin.read())

        actions: List[str] = []

        # The history archive can be renamed with running core. We need to keep
        # the list of already handled history archive files, because a new history
        # file may be created by the core during this step. All unhandled files,
        # including the current history files will be handled later when the core
        # is stopped.
        for oldname, newname in renamings:
            self._finished_history_files[(oldname, newname)] = \
                self._rename_host_in_core_history_archive(oldname, newname)
            if self._finished_history_files[(oldname, newname)]:
                actions.append("history")

        # At this place WATO already has changed it's configuration. All further
        # data might be changed by the still running core. So we need to stop
        # it now.
        core_was_running = self._core_is_running()
        if core_was_running:
            cmk.base.core.do_core_action(CoreAction.STOP, quiet=True)

        try:
            for oldname, newname in renamings:
                actions += self._rename_host_files(oldname, newname)
        finally:
            # Start monitoring again
            if core_was_running:
                # force config generation to succeed. The core *must* start.
                # TODO: Can't we drop this hack since we have config warnings now?
                core_config.ignore_ip_lookup_failures()
                AutomationStart().execute([])

                for hostname in core_config.failed_ip_lookups():
                    actions.append("dnsfail-" + hostname)

        # Convert actions into a dictionary { "what" : count }
        action_counts: Dict[str, int] = {}
        for action in actions:
            action_counts.setdefault(action, 0)
            action_counts[action] += 1

        return action_counts

    def _core_is_running(self) -> bool:
        if config.monitoring_core == "nagios":
            command = cmk.utils.paths.nagios_startscript + " status >/dev/null 2>&1"
        else:
            command = "omd status cmc >/dev/null 2>&1"
        code = os.system(command)  # nosec
        return not code

    def _rename_host_files(self, oldname: HistoryFile, newname: HistoryFile) -> List[str]:
        actions = []

        if self._rename_host_file(cmk.utils.paths.autochecks_dir, oldname + ".mk", newname + ".mk"):
            actions.append("autochecks")

        # Rename temporary files of the host
        for d in ["cache", "counters"]:
            if self._rename_host_file(cmk.utils.paths.tmp_dir + "/" + d + "/", oldname, newname):
                actions.append(d)

        if self._rename_host_dir(cmk.utils.paths.tmp_dir + "/piggyback/", oldname, newname):
            actions.append("piggyback-load")

        # Rename piggy files *created* by the host
        piggybase = cmk.utils.paths.tmp_dir + "/piggyback/"
        if os.path.exists(piggybase):
            for piggydir in os.listdir(piggybase):
                if self._rename_host_file(piggybase + piggydir, oldname, newname):
                    actions.append("piggyback-pig")

        # Logwatch
        if self._rename_host_dir(cmk.utils.paths.logwatch_dir, oldname, newname):
            actions.append("logwatch")

        # SNMP walks
        if self._rename_host_file(cmk.utils.paths.snmpwalks_dir, oldname, newname):
            actions.append("snmpwalk")

        # HW/SW-Inventory
        if self._rename_host_file(cmk.utils.paths.var_dir + "/inventory", oldname, newname):
            self._rename_host_file(cmk.utils.paths.var_dir + "/inventory", oldname + ".gz",
                                   newname + ".gz")
            actions.append("inv")

        if self._rename_host_dir(cmk.utils.paths.var_dir + "/inventory_archive", oldname, newname):
            actions.append("invarch")

        # Baked agents
        baked_agents_dir = cmk.utils.paths.var_dir + "/agents/"
        have_renamed_agent = False
        if os.path.exists(baked_agents_dir):
            for opsys in os.listdir(baked_agents_dir):
                if self._rename_host_file(baked_agents_dir + opsys, oldname, newname):
                    have_renamed_agent = True
        if have_renamed_agent:
            actions.append("agent")

        # Agent deployment
        deployment_dir = cmk.utils.paths.var_dir + "/agent_deployment/"
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
    def _omd_rename_host(self, oldname: str, newname: str) -> List[str]:
        oldregex = self._escape_name_for_regex_matching(oldname)
        actions = []

        # Temporarily stop processing of performance data
        npcd_running = os.path.exists(cmk.utils.paths.omd_root + "/tmp/pnp4nagios/run/npcd.pid")
        if npcd_running:
            os.system("omd stop npcd >/dev/null 2>&1 </dev/null")

        rrdcache_running = os.path.exists(cmk.utils.paths.omd_root + "/tmp/run/rrdcached.sock")
        if rrdcache_running:
            os.system("omd stop rrdcached >/dev/null 2>&1 </dev/null")

        try:
            # Fix pathnames in XML files
            self.rename_host_in_files(
                os.path.join(cmk.utils.paths.omd_root, "var/pnp4nagios/perfdata", oldname, "*.xml"),
                "/perfdata/%s/" % oldregex, "/perfdata/%s/" % newname)

            # RRD files
            if self._rename_host_dir(cmk.utils.paths.omd_root + "/var/pnp4nagios/perfdata", oldname,
                                     newname):
                actions.append("rrd")

            # RRD files
            if self._rename_host_dir(cmk.utils.paths.omd_root + "/var/check_mk/rrd", oldname,
                                     newname):
                actions.append("rrd")

            # entries of rrdcached journal
            if self.rename_host_in_files(os.path.join(cmk.utils.paths.omd_root,
                                                      "var/rrdcached/rrd.journal.*"),
                                         "/(perfdata|rrd)/%s/" % oldregex,
                                         "/\\1/%s/" % newname,
                                         extended_regex=True):
                actions.append("rrdcached")

            # Spoolfiles of NPCD
            if (  #
                    self.rename_host_in_files(
                        "%s/var/pnp4nagios/perfdata.dump" % cmk.utils.paths.omd_root,
                        "HOSTNAME::%s    " % oldregex,  #
                        "HOSTNAME::%s    " % newname) or  #
                    self.rename_host_in_files(
                        "%s/var/pnp4nagios/spool/perfdata.*" % cmk.utils.paths.omd_root,
                        "HOSTNAME::%s    " % oldregex,  #
                        "HOSTNAME::%s    " % newname)):
                actions.append("pnpspool")
        finally:
            if rrdcache_running:
                os.system("omd start rrdcached >/dev/null 2>&1 </dev/null")

            if npcd_running:
                os.system("omd start npcd >/dev/null 2>&1 </dev/null")

        self._rename_host_in_remaining_core_history_files(oldname, newname)

        # State retention (important for Downtimes, Acknowledgements, etc.)
        if config.monitoring_core == "nagios":
            if self.rename_host_in_files("%s/var/nagios/retention.dat" % cmk.utils.paths.omd_root,
                                         "^host_name=%s$" % oldregex,
                                         "host_name=%s" % newname,
                                         extended_regex=True):
                actions.append("retention")

        else:  # CMC
            # Create a file "renamed_hosts" with the information about the
            # renaming of the hosts. The core will honor this file when it
            # reads the status file with the saved state.
            open(cmk.utils.paths.var_dir + "/core/renamed_hosts",
                 "w").write("%s\n%s\n" % (oldname, newname))
            actions.append("retention")

        # NagVis maps
        if self.rename_host_in_files("%s/etc/nagvis/maps/*.cfg" % cmk.utils.paths.omd_root,
                                     "^[[:space:]]*host_name=%s[[:space:]]*$" % oldregex,
                                     "host_name=%s" % newname,
                                     extended_regex=True):
            actions.append("nagvis")

        return actions

    def _rename_host_in_remaining_core_history_files(self, oldname: str, newname: str) -> List[str]:
        """Perform the rename operation in all history archive files that have not been handled yet"""
        finished_file_paths = self._finished_history_files[(oldname, newname)]
        all_file_paths = set(self._get_core_history_files(only_archive=False))
        todo_file_paths = list(all_file_paths.difference(finished_file_paths))
        return self._rename_host_in_core_history_files(todo_file_paths, oldname, newname)

    def _rename_host_in_core_history_archive(self, oldname: str, newname: str) -> List[str]:
        """Perform the rename operation in all history archive files"""
        file_paths = self._get_core_history_files(only_archive=True)
        return self._rename_host_in_core_history_files(file_paths, oldname, newname)

    def _get_core_history_files(self, only_archive: bool) -> List[str]:
        path_patterns = [
            "var/check_mk/core/archive/*",
            "var/nagios/archive/*",
        ]

        if not only_archive:
            path_patterns += [
                "var/check_mk/core/history",
                "var/nagios/nagios.log",
            ]

        file_paths: List[str] = []
        for path_pattern in path_patterns:
            file_paths += glob.glob("%s/%s" % (cmk.utils.paths.omd_root, path_pattern))
        return file_paths

    def _rename_host_in_core_history_files(self, file_paths: List[str], oldname: str,
                                           newname: str) -> List[str]:
        oldregex = self._escape_name_for_regex_matching(oldname)

        # Logfiles and history files of CMC and Nagios. Problem
        # here: the exact place of the hostname varies between the
        # various log entry lines
        sed_commands = r'''
s/(INITIAL|CURRENT) (HOST|SERVICE) STATE: %(old)s;/\1 \2 STATE: %(new)s;/
s/(HOST|SERVICE) (DOWNTIME |FLAPPING |)ALERT: %(old)s;/\1 \2ALERT: %(new)s;/
s/PASSIVE (HOST|SERVICE) CHECK: %(old)s;/PASSIVE \1 CHECK: %(new)s;/
s/(HOST|SERVICE) NOTIFICATION: ([^;]+);%(old)s;/\1 NOTIFICATION: \2;%(new)s;/
''' % {
            "old": oldregex,
            "new": newname
        }

        handled_files: List[str] = []

        command = ["sed", "-ri", "--file=/dev/fd/0"]
        p = subprocess.Popen(
            command + file_paths,
            stdin=subprocess.PIPE,
            stdout=open(os.devnull, "w"),
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
        p.communicate(input=sed_commands.encode("utf-8"))
        # TODO: error handling?

        handled_files += file_paths

        return handled_files

    # Returns True in case files were found, otherwise False
    def rename_host_in_files(self,
                             path_pattern: str,
                             old: str,
                             new: str,
                             extended_regex: bool = False) -> bool:
        paths = glob.glob(path_pattern)
        if paths:
            extended = ["-r"] if extended_regex else []
            subprocess.call(["sed", "-i"] + extended + ["s@%s@%s@" % (old, new)] + paths,
                            stderr=open(os.devnull, "w"))
            return True

        return False

    def _escape_name_for_regex_matching(self, name: str) -> str:
        return name.replace(".", "[.]")


automations.register(AutomationRenameHosts())


class AutomationAnalyseServices(Automation):
    cmd = "analyse-service"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: List[str]) -> Dict:
        hostname = args[0]
        servicedesc = args[1]

        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        service_info = self._get_service_info(config_cache, host_config, servicedesc)
        if service_info:
            service_info.update({
                "labels": config_cache.labels_of_service(hostname, servicedesc),
                "label_sources": config_cache.label_sources_of_service(hostname, servicedesc),
            })
        return service_info

    # Determine the type of the check, and how the parameters are being
    # constructed
    # TODO: Refactor this huge function
    # TODO: Was ist mit Clustern???
    # TODO: Klappt das mit automatischen verschatten von SNMP-Checks (bei dual Monitoring)
    def _get_service_info(self, config_cache: config.ConfigCache, host_config: config.HostConfig,
                          servicedesc: str) -> Dict:
        hostname = host_config.hostname
        check_api_utils.set_hostname(hostname)

        # We just consider types of checks that are managed via WATO.
        # We have the following possible types of services:
        # 1. manual checks (static_checks) (currently overriding inventorized checks)
        # 2. inventorized check
        # 3. classical checks
        # 4. active checks

        # 1. Manual checks
        for checkgroup_name, checktype, item, params in host_config.static_checks:
            # TODO (mo): centralize maincheckify: CMK-4295
            check_plugin_name = CheckPluginName(maincheckify(checktype))
            descr = config.service_description(hostname, check_plugin_name, item)
            if descr == servicedesc:
                return {
                    "origin": "static",
                    "checkgroup": checkgroup_name,
                    "checktype": checktype,
                    "item": item,
                    "parameters": params,
                }

        # TODO: There is a lot of duplicated logic with discovery.py/check_table.py. Clean this
        # whole function up.
        if host_config.is_cluster:
            services: List[cmk.base.check_utils.Service] = []
            for node in host_config.nodes or []:
                for service in config_cache.get_autochecks_of(node):
                    if hostname == config_cache.host_of_clustered_service(
                            node, service.description):
                        services += services
        else:
            services = config_cache.get_autochecks_of(hostname)

        table = check_table.get_check_table(hostname)
        # 2. Load all autochecks of the host in question and try to find
        # our service there
        for service in services:

            if service.id() not in table:
                continue  # this is a clustered service

            if service.description != servicedesc:
                continue

            plugin = agent_based_register.get_check_plugin(service.check_plugin_name)
            if plugin is None:
                # Just to be safe, and to let mypy know.
                # plugin should never be None for services that are in the check_table.
                continue

            check_parameters = service.parameters
            if isinstance(check_parameters, cmk.base.config.TimespecificParamList):
                check_parameters = cmk.base.checking.legacy_determine_check_params(check_parameters)
                check_parameters = {
                    "tp_computed_params": {
                        "params": check_parameters,
                        "computed_at": time.time()
                    }
                }

            return {
                "origin": "auto",
                "checktype": str(plugin.name),
                "checkgroup": str(plugin.check_ruleset_name),
                "item": service.item,
                "inv_parameters": service.parameters,
                "factory_settings": plugin.check_default_parameters,
                "parameters": check_parameters,
            }

        # 3. Classical checks
        for entry in host_config.custom_checks:
            desc = entry["service_description"]
            if desc == servicedesc:
                result = {
                    "origin": "classic",
                }
                if "command_line" in entry:  # Only active checks have a command line
                    result["command_line"] = entry["command_line"]
                return result

        # 4. Active checks
        for plugin_name, entries in host_config.active_checks:
            for active_check_params in entries:
                description = config.active_check_service_description(hostname, plugin_name,
                                                                      active_check_params)
                if description == servicedesc:
                    return {
                        "origin": "active",
                        "checktype": plugin_name,
                        "parameters": active_check_params,
                    }

        return {}  # not found


automations.register(AutomationAnalyseServices())


class AutomationAnalyseHost(Automation):
    cmd = "analyse-host"
    needs_config = True
    needs_checks = False

    def execute(self, args: List[str]) -> Dict:
        host_name = args[0]
        config_cache = config.get_config_cache()
        return {
            "labels": config_cache.get_host_config(host_name).labels,
            "label_sources": config_cache.get_host_config(host_name).label_sources,
        }


automations.register(AutomationAnalyseHost())


class AutomationDeleteHosts(Automation):
    cmd = "delete-hosts"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: List[str]) -> None:
        for hostname in args:
            self._delete_host_files(hostname)

    def _delete_host_files(self, hostname: HostName) -> None:

        # The inventory_archive as well as the performance data is kept
        # we do not want to loose any historic data for accidently deleted hosts.
        #
        # These files are cleaned up by the disk space mechanism.

        # single files
        for path in [
                "%s/%s" % (cmk.utils.paths.precompiled_hostchecks_dir, hostname),
                "%s/%s.py" % (cmk.utils.paths.precompiled_hostchecks_dir, hostname),
                "%s/%s.mk" % (cmk.utils.paths.autochecks_dir, hostname),
                "%s/%s" % (cmk.utils.paths.counters_dir, hostname),
                "%s/%s" % (cmk.utils.paths.tcp_cache_dir, hostname),
                "%s/persisted/%s" % (cmk.utils.paths.var_dir, hostname),
                "%s/inventory/%s" % (cmk.utils.paths.var_dir, hostname),
                "%s/inventory/%s.gz" % (cmk.utils.paths.var_dir, hostname),
                "%s/agent_deployment/%s" % (cmk.utils.paths.var_dir, hostname),
        ]:
            self._delete_if_exists(path)

        try:
            ds_directories = os.listdir(cmk.utils.paths.data_source_cache_dir)
        except OSError as e:
            if e.errno == errno.ENOENT:
                ds_directories = []
            else:
                raise

        for data_source_name in ds_directories:
            filename = "%s/%s/%s" % (cmk.utils.paths.data_source_cache_dir, data_source_name,
                                     hostname)
            self._delete_if_exists(filename)

        # softlinks for baked agents. obsolete packages are removed upon next bake action
        # TODO: Move to bakery code
        baked_agents_dir = cmk.utils.paths.var_dir + "/agents/"
        if os.path.exists(baked_agents_dir):
            for folder in os.listdir(baked_agents_dir):
                self._delete_if_exists("%s/%s" % (folder, hostname))

        # logwatch and piggyback folders
        for what_dir in [
                "%s/%s" % (cmk.utils.paths.logwatch_dir, hostname),
                "%s/piggyback/%s" % (cmk.utils.paths.tmp_dir, hostname),
        ]:
            try:
                shutil.rmtree(what_dir)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

    def _delete_if_exists(self, path: str) -> None:
        """Delete the given file in case it exists"""
        try:
            os.unlink(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise


automations.register(AutomationDeleteHosts())


class AutomationRestart(Automation):
    cmd = "restart"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def _mode(self) -> CoreAction:
        if config.monitoring_core == "cmc" and not self._check_plugins_have_changed():
            return CoreAction.RELOAD
        return CoreAction.RESTART

    def execute(self, args: List[str]) -> core_config.ConfigurationWarnings:
        with redirect_stdout(open(os.devnull, "w")):
            try:
                do_restart(create_core(config.monitoring_core), self._mode())
            except (MKBailOut, MKGeneralException) as e:
                raise MKAutomationError(str(e))

            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                raise MKAutomationError(str(e))

            return core_config.get_configuration_warnings()

    def _check_plugins_have_changed(self) -> bool:
        this_time = self._last_modification_in_dir(str(cmk.utils.paths.local_checks_dir))
        last_time = self._time_of_last_core_restart()
        return this_time > last_time

    def _last_modification_in_dir(self, dir_path: str) -> float:
        max_time = os.stat(dir_path).st_mtime
        for file_name in os.listdir(dir_path):
            max_time = max(max_time, os.stat(dir_path + "/" + file_name).st_mtime)
        return max_time

    def _time_of_last_core_restart(self) -> float:
        if config.monitoring_core == "cmc":
            pidfile_path = cmk.utils.paths.omd_root + "/tmp/run/cmc.pid"
        else:
            pidfile_path = cmk.utils.paths.omd_root + "/tmp/lock/nagios.lock"

        if os.path.exists(pidfile_path):
            return os.stat(pidfile_path).st_mtime

        return 0.0


automations.register(AutomationRestart())


class AutomationReload(AutomationRestart):
    cmd = "reload"

    def _mode(self) -> CoreAction:
        if self._check_plugins_have_changed():
            return CoreAction.RESTART
        return CoreAction.RELOAD


automations.register(AutomationReload())


class AutomationStart(AutomationRestart):
    """Not an externally registered automation, just supporting the "rename-hosts" automation"""
    cmd = "start"

    def _mode(self) -> CoreAction:
        return CoreAction.START


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

    def execute(self, args: List[str]) -> Dict[str, Any]:
        config.load(with_conf_d=False)

        # We read the list of variable names from stdin since
        # that could be too much for the command line
        variable_names = ast.literal_eval(sys.stdin.read())

        missing_variables = [v for v in variable_names if not hasattr(config, v)]

        if missing_variables:
            config.load_all_agent_based_plugins(check_api.get_check_api_context)
            config.load(with_conf_d=False)

        result = {}
        for varname in variable_names:
            if hasattr(config, varname):
                value = getattr(config, varname)
                if not hasattr(value, '__call__'):
                    result[varname] = value
        return result


automations.register(AutomationGetConfiguration())


class AutomationGetCheckInformation(Automation):
    cmd = "get-check-information"
    needs_config = False
    needs_checks = True

    def execute(self, args: List[str]) -> Dict[CheckPluginNameStr, Dict[str, Any]]:
        manuals = man_pages.all_man_pages()

        plugin_infos: Dict[CheckPluginNameStr, Dict[str, Any]] = {}
        for plugin in agent_based_register.iter_all_check_plugins():
            plugin_info = plugin_infos.setdefault(
                str(plugin.name), {
                    "title": self._get_title(manuals, plugin),
                    "name": str(plugin.name),
                    "service_description": str(plugin.service_name),
                })
            if plugin.check_ruleset_name:
                plugin_info["check_ruleset_name"] = str(plugin.check_ruleset_name)
                # TODO: kept for compatibility. See if we can drop this.
                plugin_info["group"] = str(plugin.check_ruleset_name)
            if plugin.discovery_ruleset_name:
                plugin_info["discovery_ruleset_name"] = str(plugin.discovery_ruleset_name)

        return plugin_infos

    @staticmethod
    def _get_title(manuals, plugin) -> str:
        manfile = manuals.get(str(plugin.name))
        if manfile:
            try:
                return cmk.utils.man_pages.get_title_from_man_page(Path(manfile))
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                raise MKAutomationError("Failed to parse man page '%s': %s" % (plugin.name, e))
        return str(plugin.name)


automations.register(AutomationGetCheckInformation())


class AutomationGetSectionInformation(Automation):
    cmd = "get-section-information"
    needs_config = False
    needs_checks = True

    def execute(self, args: List[str]) -> Dict[str, Dict[str, str]]:

        section_infos = {
            str(section.name): {
                # for now, we need only these two.
                "name": str(section.name),
                "type": "agent",
            } for section in agent_based_register.iter_all_agent_sections()
        }
        section_infos.update({
            str(section.name): {
                "name": str(section.name),
                "type": "snmp",
            } for section in agent_based_register.iter_all_snmp_sections()
        })
        return section_infos


automations.register(AutomationGetSectionInformation())


class AutomationGetRealTimeChecks(Automation):
    cmd = "get-real-time-checks"
    needs_config = False
    needs_checks = True

    def execute(self, args: List[str]) -> List[Tuple[CheckPluginNameStr, str]]:
        manuals = man_pages.all_man_pages()

        rt_checks = []
        for check_plugin_name, check in config.check_info.items():
            if check["handle_real_time_checks"]:
                title = ensure_str(check_plugin_name)
                try:
                    manfile = manuals.get(check_plugin_name)
                    if manfile:
                        title = cmk.utils.man_pages.get_title_from_man_page(Path(manfile))
                except Exception:
                    if cmk.utils.debug.enabled():
                        raise

                rt_checks.append(
                    (check_plugin_name, u"%s - %s" % (ensure_str(check_plugin_name), title)))

        return rt_checks


automations.register(AutomationGetRealTimeChecks())


class AutomationScanParents(Automation):
    cmd = "scan-parents"
    needs_config = True
    needs_checks = True

    def execute(self, args: List[str]) -> cmk.base.parent_scan.Gateways:
        settings = {
            "timeout": int(args[0]),
            "probes": int(args[1]),
            "max_ttl": int(args[2]),
            "ping_probes": int(args[3]),
        }
        hostnames = args[4:]
        if not cmk.base.parent_scan.traceroute_available():
            raise MKAutomationError("Cannot find binary <tt>traceroute</tt> in search path.")
        config_cache = config.get_config_cache()

        try:
            gateways = cmk.base.parent_scan.scan_parents_of(config_cache,
                                                            hostnames,
                                                            silent=True,
                                                            settings=settings)
            return gateways
        except Exception as e:
            raise MKAutomationError("%s" % e)


automations.register(AutomationScanParents())


class AutomationDiagHost(Automation):
    cmd = "diag-host"
    needs_config = True
    needs_checks = True

    def execute(self, args: List[str]) -> Tuple[int, str]:
        hostname, test, ipaddress, snmp_community = args[:4]
        agent_port, snmp_timeout, snmp_retries = map(int, args[4:7])

        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

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

        if not ipaddress:
            try:
                resolved_address = ip_lookup.lookup_ip_address(host_config)
            except Exception:
                raise MKGeneralException("Cannot resolve hostname %s into IP address" % hostname)

            if resolved_address is None:
                raise MKGeneralException("Cannot resolve hostname %s into IP address" % hostname)

            ipaddress = resolved_address

        try:
            if test == 'ping':
                return self._execute_ping(host_config, ipaddress)

            if test == 'agent':
                return self._execute_agent(
                    host_config,
                    ipaddress,
                    agent_port=agent_port,
                    cmd=cmd,
                    tcp_connect_timeout=tcp_connect_timeout,
                )

            if test == 'traceroute':
                return self._execute_traceroute(host_config, ipaddress)

            if test.startswith('snmp'):
                return self._execute_snmp(
                    test,
                    host_config,
                    hostname,
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

            return 1, "Command not implemented"

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            return 1, str(e)

    def _execute_ping(self, host_config: config.HostConfig, ipaddress: str) -> Tuple[int, str]:
        base_cmd = "ping6" if host_config.is_ipv6_primary else "ping"
        p = subprocess.Popen(
            [base_cmd, "-A", "-i", "0.2", "-c", "2", "-W", "5", ipaddress],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if p.stdout is None:
            raise RuntimeError()
        response = p.stdout.read()
        return p.wait(), response

    def _execute_agent(
        self,
        host_config: config.HostConfig,
        ipaddress: HostAddress,
        agent_port: int,
        cmd: str,
        tcp_connect_timeout: Optional[float],
    ) -> Tuple[int, str]:
        state, output = 0, u""
        for source in checkers.make_sources(
                host_config,
                ipaddress,
                mode=checkers.Mode.CHECKING,
        ):
            source.file_cache_max_age = config.check_max_cachefile_age
            if isinstance(source, checkers.programs.DSProgramSource) and cmd:
                source = source.ds(
                    source.hostname,
                    source.ipaddress,
                    mode=source.mode,
                    template=cmd,
                )
            elif isinstance(source, checkers.tcp.TCPSource):
                source.port = agent_port
                if tcp_connect_timeout is not None:
                    source.timeout = tcp_connect_timeout
            elif isinstance(source, checkers.snmp.SNMPSource):
                continue

            raw_data = source.fetch()
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

    def _execute_traceroute(self, host_config: config.HostConfig,
                            ipaddress: str) -> Tuple[int, str]:
        family_flag = "-6" if host_config.is_ipv6_primary else "-4"
        try:
            p = subprocess.Popen(
                ['traceroute', family_flag, '-n', ipaddress],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
            )
        except OSError as e:
            if e.errno == errno.ENOENT:
                return 1, "Cannot find binary <tt>traceroute</tt>."
            raise
        if p.stdout is None:
            raise RuntimeError()
        return p.wait(), p.stdout.read()

    def _execute_snmp(
        self,
        test,
        host_config,
        hostname,
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
    ):
        snmp_config = host_config.snmp_config(ipaddress)

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
                    if not isinstance(snmpv3_auth_proto, str) \
                        or not isinstance(snmpv3_security_name, str) \
                        or not isinstance(snmpv3_security_password, str):
                        raise TypeError()
                    snmpv3_credentials.extend(
                        [snmpv3_auth_proto, snmpv3_security_name, snmpv3_security_password])
                else:
                    if not isinstance(snmpv3_security_name, str):
                        raise TypeError()
                    snmpv3_credentials.extend([snmpv3_security_name])

                if snmpv3_use == "authPriv":
                    if not isinstance(snmpv3_privacy_proto, str) or not isinstance(
                            snmpv3_privacy_password, str):
                        raise TypeError()
                    snmpv3_credentials.extend([snmpv3_privacy_proto, snmpv3_privacy_password])

                credentials = tuple(snmpv3_credentials)
        elif snmp_community:
            credentials = snmp_community

        # Determine SNMPv2/v3 community
        if hostname not in config.explicit_snmp_communities:
            cred = host_config.snmp_credentials_of_version(
                snmp_version=3 if test == "snmpv3" else 2)
            if cred is not None:
                credentials = cred

        # SNMP versions
        if test in ['snmpv2', 'snmpv3']:
            is_bulkwalk_host = True
            is_snmpv2or3_without_bulkwalk_host = False
        elif test == 'snmpv2_nobulk':
            is_bulkwalk_host = False
            is_snmpv2or3_without_bulkwalk_host = True
        elif test == 'snmpv1':
            is_bulkwalk_host = False
            is_snmpv2or3_without_bulkwalk_host = False

        else:
            return 1, "SNMP command not implemented"

        #TODO: What about SNMP management boards?
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
                'timeout': snmp_timeout,
                'retries': snmp_retries,
            },
            oid_range_limits=snmp_config.oid_range_limits,
            snmpv3_contexts=snmp_config.snmpv3_contexts,
            character_encoding=snmp_config.character_encoding,
            is_usewalk_host=snmp_config.is_usewalk_host,
            is_inline_snmp_host=snmp_config.is_inline_snmp_host,
            record_stats=config.record_inline_snmp_stats,
        )

        data = snmp_table.get_snmp_table_cached(
            None,
            SNMPTree(base='.1.3.6.1.2.1.1', oids=['1.0', '4.0', '5.0', '6.0']),
            backend=factory.backend(snmp_config, log.logger),
        )

        if data:
            return 0, 'sysDescr:\t%s\nsysContact:\t%s\nsysName:\t%s\nsysLocation:\t%s\n' % tuple(
                data[0])

        return 1, 'Got empty SNMP response'


automations.register(AutomationDiagHost())


class AutomationActiveCheck(Automation):
    cmd = "active-check"
    needs_config = True
    needs_checks = True

    def execute(self, args: List[str]) -> Optional[Tuple[ServiceState, ServiceDetails]]:
        hostname, plugin, raw_item = args
        item = raw_item

        host_config = config.get_config_cache().get_host_config(hostname)

        if plugin == "custom":
            for entry in host_config.custom_checks:
                if entry["service_description"] != item:
                    continue

                command_line = self._replace_core_macros(hostname, entry.get("command_line", ""))
                if command_line:
                    cmd = core_config.autodetect_plugin(command_line)
                    return self._execute_check_plugin(cmd)

                return -1, "Passive check - cannot be executed"

        try:
            act_info = config.active_check_info[plugin]
        except KeyError:
            return None

        # Set host name for host_name()-function (part of the Check API)
        # (used e.g. by check_http)
        check_api_utils.set_hostname(hostname)

        for params in dict(host_config.active_checks).get(plugin, []):
            description = config.active_check_service_description(hostname, plugin, params)
            if description != item:
                continue

            command_args = core_config.active_check_arguments(hostname, description,
                                                              act_info["argument_function"](params))
            command_line = self._replace_core_macros(
                hostname, act_info["command_line"].replace("$ARG1$", command_args))
            cmd = core_config.autodetect_plugin(command_line)
            return self._execute_check_plugin(cmd)

        return None

    def _load_resource_file(self, macros: Dict[str, str]) -> None:
        try:
            for line in open(cmk.utils.paths.omd_root + "/etc/nagios/resource.cfg"):
                line = line.strip()
                if not line or line[0] == '#':
                    continue
                varname, value = line.split('=', 1)
                macros[varname] = value
        except Exception:
            if cmk.utils.debug.enabled():
                raise

    # Simulate replacing some of the more important macros of hosts. We
    # cannot use dynamic macros, of course. Note: this will not work
    # without OMD, since we do not know the value of $USER1$ and $USER2$
    # here. We could read the Nagios resource.cfg file, but we do not
    # know for sure the place of that either.
    def _replace_core_macros(self, hostname: HostName, commandline: str) -> str:
        config_cache = config.get_config_cache()
        macros = core_config.get_host_macros_from_attributes(
            hostname, core_config.get_host_attributes(hostname, config_cache))
        self._load_resource_file(macros)
        for varname, value in macros.items():
            commandline = commandline.replace(varname, "%s" % value)
        return commandline

    def _execute_check_plugin(self, commandline: str) -> Tuple[ServiceState, ServiceDetails]:
        try:
            p = os.popen(commandline + " 2>&1")  # nosec
            output = p.read().strip()
            ret = p.close()
            if not ret:
                status = 0
            else:
                if ret & 0xff == 0:
                    status = ret >> 8
                else:
                    status = 3
            if status < 0 or status > 3:
                status = 3
            output = output.split("|", 1)[0]  # Drop performance data
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

    def execute(self, args: List[str]) -> ip_lookup.UpdateDNSCacheResult:
        return ip_lookup.update_dns_cache()


automations.register(AutomationUpdateDNSCache())


class AutomationGetAgentOutput(Automation):
    cmd = "get-agent-output"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: List[str]) -> Tuple[bool, ServiceDetails, bytes]:
        hostname, ty = args
        host_config = config.HostConfig.make_host_config(hostname)

        success = True
        output = u""
        info = b""

        try:
            ipaddress = ip_lookup.lookup_ip_address(host_config)
            if ty == "agent":
                checkers.FileCacheFactory.reset_maybe()
                for source in checkers.make_sources(
                        host_config,
                        ipaddress,
                        mode=checkers.Mode.CHECKING,
                ):
                    source.file_cache_max_age = config.check_max_cachefile_age
                    if not isinstance(source, checkers.agent.AgentSource):
                        continue

                    raw_data = source.fetch()
                    host_sections = source.parse(raw_data)
                    source_state, source_output, _source_perfdata = source.summarize(host_sections)
                    if source_state != 0:
                        # Optionally show errors of problematic data sources
                        success = False
                        output += "[%s] %s\n" % (source.id, source_output)
                    assert raw_data.ok is not None
                    info += raw_data.ok
            else:
                if not ipaddress:
                    raise MKGeneralException("Failed to gather IP address of %s" % hostname)
                snmp_config = config.HostConfig.make_snmp_config(hostname, ipaddress)
                backend = factory.backend(snmp_config, log.logger, use_cache=False)

                lines = []
                for walk_oid in snmp_modes.oids_to_walk():
                    try:
                        for oid, value in snmp_modes.walk_for_export(walk_oid, backend=backend):
                            raw_oid_value = "%s %s\n" % (oid, value)
                            lines.append(ensure_binary(raw_oid_value))
                    except Exception as e:
                        if cmk.utils.debug.enabled():
                            raise
                        success = False
                        output += "OID '%s': %s\n" % (oid, e)

                info = b"".join(lines)
        except Exception as e:
            success = False
            output = "Failed to fetch data from %s: %s\n" % (hostname, e)
            if cmk.utils.debug.enabled():
                raise

        return success, output, info


automations.register(AutomationGetAgentOutput())


class AutomationNotificationReplay(Automation):
    cmd = "notification-replay"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: List[str]) -> None:
        nr = args[0]
        return notify.notification_replay_backlog(int(nr))


automations.register(AutomationNotificationReplay())


class AutomationNotificationAnalyse(Automation):
    cmd = "notification-analyse"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args: List[str]) -> Optional[notify.NotifyAnalysisInfo]:
        nr = args[0]
        return notify.notification_analyse_backlog(int(nr))


automations.register(AutomationNotificationAnalyse())


class AutomationGetBulks(Automation):
    cmd = "notification-get-bulks"
    needs_config = False
    needs_checks = False

    def execute(self, args: List[str]) -> notify.NotifyBulks:
        only_ripe = args[0] == "1"
        return notify.find_bulks(only_ripe)


automations.register(AutomationGetBulks())


class AutomationGetServiceConfigurations(Automation):
    cmd = "get-service-configurations"
    needs_config = True
    needs_checks = True

    def execute(self, args: List[str]) -> Dict:
        result: Dict = {"hosts": {}}
        config_cache = config.get_config_cache()
        for hostname in config_cache.all_active_hosts():
            host_config = config_cache.get_host_config(hostname)
            result["hosts"][hostname] = self._get_config_for_host(host_config)

        result["checkgroup_of_checks"] = self._get_checkgroup_of_checks()
        return result

    def _get_config_for_host(
            self, host_config: config.HostConfig) -> Dict[str, List[Tuple[str, str, Any]]]:
        return {
            "checks": [(str(s.check_plugin_name), s.description, s.parameters)
                       for s in check_table.get_check_table(host_config.hostname).values()],
            "active_checks": self._get_active_checks(host_config)
        }

    def _get_active_checks(self, host_config: config.HostConfig) -> List[Tuple[str, str, Any]]:
        actchecks = []
        for plugin_name, entries in host_config.active_checks:
            for params in entries:
                description = config.active_check_service_description(host_config.hostname,
                                                                      plugin_name, params)
                actchecks.append((plugin_name, description, params))
        return actchecks

    def _get_checkgroup_of_checks(self) -> Dict[str, Optional[str]]:
        return {
            str(plugin.name): str(plugin.check_ruleset_name) if plugin.check_ruleset_name else None
            for plugin in agent_based_register.iter_all_check_plugins()
        }


automations.register(AutomationGetServiceConfigurations())


class AutomationGetLabelsOf(Automation):
    cmd = "get-labels-of"
    needs_config = True
    needs_checks = False

    def execute(self, args: List[str]) -> Dict[str, Any]:
        object_type, host_name = args[:2]

        config_cache = config.get_config_cache()

        if object_type == "host":
            return {
                "labels": config_cache.get_host_config(host_name).labels,
                "label_sources": config_cache.get_host_config(host_name).label_sources,
            }

        if object_type == "service":
            service_description = args[2]
            return {
                "labels": config_cache.labels_of_service(host_name, service_description),
                "label_sources": config_cache.label_sources_of_service(
                    host_name, service_description),
            }

        raise NotImplementedError()


automations.register(AutomationGetLabelsOf())


class AutomationCreateDiagnosticsDump(Automation):
    cmd = "create-diagnostics-dump"
    needs_config = False
    needs_checks = False

    def execute(self, args: DiagnosticsCLParameters) -> Dict[str, Any]:
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            log.setup_console_logging()
            dump = DiagnosticsDump(deserialize_cl_parameters(args))
            dump.create()
            return {
                "output": buf.getvalue(),
                "tarfile_path": str(dump.tarfile_path),
                "tarfile_created": dump.tarfile_created,
            }


automations.register(AutomationCreateDiagnosticsDump())
