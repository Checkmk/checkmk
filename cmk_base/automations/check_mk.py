#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import ast
import errno
import glob
import os
import subprocess
import sys
import time
import shutil
import cStringIO
import contextlib
from typing import Tuple, Optional, Dict, Any, Text, List  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.debug
import cmk.utils.man_pages as man_pages
from cmk.utils.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.config as config
import cmk_base.core
import cmk_base.core_config as core_config
import cmk_base.snmp as snmp
import cmk_base.snmp_utils as snmp_utils
import cmk_base.discovery as discovery
import cmk_base.check_table as check_table
from cmk_base.automations import automations, Automation, MKAutomationError
import cmk_base.check_utils
import cmk_base.autochecks
import cmk_base.nagios_utils
from cmk_base.core_factory import create_core
import cmk_base.check_api_utils as check_api_utils
import cmk_base.check_api as check_api
import cmk_base.parent_scan
import cmk_base.notify as notify
import cmk_base.ip_lookup as ip_lookup
import cmk_base.data_sources as data_sources


class DiscoveryAutomation(Automation):
    # if required, schedule an inventory check
    def _trigger_discovery_check(self, host_config):
        # TODO: Check the last condition ("or host_config.nodes"). Is this really correct?
        if (config.inventory_check_autotrigger and config.inventory_check_interval) and\
                (not host_config.is_cluster or host_config.nodes):
            discovery.schedule_discovery_check(host_config.hostname)


class AutomationDiscovery(DiscoveryAutomation):
    cmd = "inventory"  # TODO: Rename!
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    # Does discovery for a list of hosts. Possible values for how:
    # "new" - find only new services (like -I)
    # "remove" - remove exceeding services
    # "fixall" - find new, remove exceeding
    # "refresh" - drop all services and reinventorize
    # Hosts on the list that are offline (unmonitored) will
    # be skipped.
    def execute(self, args):
        # Error sensivity
        if args[0] == "@raiseerrors":
            args = args[1:]
            on_error = "raise"
            os.dup2(os.open("/dev/null", os.O_WRONLY), 2)
        else:
            on_error = "ignore"

        # perform full SNMP scan on SNMP devices?
        if args[0] == "@scan":
            do_snmp_scan = True
            args = args[1:]
        else:
            do_snmp_scan = False

        # use cache files if present?
        # TODO: Why is this handling inconsistent with try-inventory?
        if args[0] == "@cache":
            args = args[1:]
            use_caches = True
        else:
            use_caches = False

        if len(args) < 2:
            raise MKAutomationError("Need two arguments: new|remove|fixall|refresh HOSTNAME")

        how = args[0]
        hostnames = args[1:]

        config_cache = config.get_config_cache()

        counts = {}
        failed_hosts = {}

        for hostname in hostnames:
            host_config = config_cache.get_host_config(hostname)
            result, error = discovery.discover_on_host(config_cache, host_config, how, do_snmp_scan,
                                                       use_caches, on_error)
            counts[hostname] = [
                result["self_new"], result["self_removed"], result["self_kept"],
                result["self_total"]
            ]

            if error is not None:
                failed_hosts[hostname] = error
            else:
                self._trigger_discovery_check(host_config)

        return counts, failed_hosts


automations.register(AutomationDiscovery())


# Python 3? use contextlib.redirect_stdout
@contextlib.contextmanager
def redirect_output(where):
    """Redirects stdout/stderr to the given file like object"""
    prev_stdout, prev_stderr = sys.stdout, sys.stderr
    prev_stdout.flush()
    prev_stderr.flush()
    sys.stdout = sys.stderr = where
    try:
        yield where
    finally:
        where.flush()
        sys.stdout, sys.stderr = prev_stdout, prev_stderr


class AutomationTryDiscovery(Automation):
    cmd = "try-inventory"  # TODO: Rename!
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args):
        with redirect_output(cStringIO.StringIO()) as buf:
            cmk.utils.log.setup_console_logging()
            cmk.utils.log.set_verbosity(1)
            result = self._execute_discovery(args)
            return {"output": buf.getvalue(), "check_table": result}

    def _execute_discovery(self, args):
        use_caches = False
        do_snmp_scan = False
        if args[0] == '@noscan':
            args = args[1:]
            do_snmp_scan = False
            use_caches = True
            data_sources.abstract.DataSource.set_use_outdated_cache_file()
            data_sources.tcp.TCPDataSource.use_only_cache()

        elif args[0] == '@scan':
            args = args[1:]
            do_snmp_scan = True
            use_caches = False

        if args[0] == '@raiseerrors':
            on_error = "raise"
            args = args[1:]
        else:
            on_error = "ignore"

        data_sources.abstract.DataSource.set_may_use_cache_file(use_caches)
        hostname = args[0]
        table = discovery.get_check_preview(
            hostname, use_caches=use_caches, do_snmp_scan=do_snmp_scan, on_error=on_error)

        # Content of one row
        # check_source, check_plugin_name, checkgroup, item, paramstring, params, descr, exitcode, output, perfdata

        now = time.time()
        for idx, row in enumerate(table):
            params = row[5]
            # This isinstance check is also done within determine check_params,
            # but the explicit check here saves performance
            if isinstance(params, cmk_base.config.TimespecificParamList):
                new_params = cmk_base.checking.determine_check_params(params)
                # Since the row is a tuple, we cannot simply replace an entry..
                new_row = list(row)
                new_row[5] = {"tp_computed_params": {"params": new_params, "computed_at": now}}
                table[idx] = tuple(new_row)

        return table


automations.register(AutomationTryDiscovery())


class AutomationSetAutochecks(DiscoveryAutomation):
    cmd = "set-autochecks"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    # Set the new list of autochecks. This list is specified by a
    # table of (checktype, item). No parameters are specified. Those
    # are either (1) kept from existing autochecks or (2) computed
    # from a new inventory. Note: we must never convert check parameters
    # from python source code to actual values.
    def execute(self, args):
        hostname = args[0]
        new_items = ast.literal_eval(sys.stdin.read())

        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        discovery.set_autochecks_of(host_config, new_items)
        self._trigger_discovery_check(host_config)
        return None


automations.register(AutomationSetAutochecks())


# TODO: Is this automation still needed?
class AutomationGetAutochecks(Automation):
    cmd = "get-autochecks"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args):
        hostname = args[0]
        result = []
        for ct, item, paramstring in discovery.parse_autochecks_file(hostname):
            result.append((ct, item, discovery.resolve_paramstring(ct, paramstring), paramstring))
        return result


automations.register(AutomationGetAutochecks())


class AutomationRenameHosts(Automation):
    cmd = "rename-hosts"
    needs_config = True
    needs_checks = True

    def __init__(self):
        super(AutomationRenameHosts, self).__init__()
        self._finished_history_files = {}

    # WATO calls this automation when hosts have been renamed. We need to change
    # several file and directory names. This function has no argument but reads
    # Python pair-list from stdin:
    # [("old1", "new1"), ("old2", "new2")])
    def execute(self, args):
        renamings = ast.literal_eval(sys.stdin.read())

        actions = []

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
            cmk_base.core.do_core_action("stop", quiet=True)

        try:
            for oldname, newname in renamings:
                # Autochecks: simply read and write out the file again. We do
                # not store a host name here anymore - but old versions did.
                # by rewriting we get rid of the host name.
                actions += self._rename_host_autochecks(oldname, newname)
                actions += self._rename_host_files(oldname, newname)
        finally:
            # Start monitoring again
            if core_was_running:
                # force config generation to succeed. The core *must* start.
                # TODO: Can't we drop this hack since we have config warnings now?
                core_config.ignore_ip_lookup_failures()
                # TODO: Clean this up!
                restart = AutomationRestart()
                restart._mode = lambda: "start"
                restart.execute([])

                for hostname in core_config.failed_ip_lookups():
                    actions.append("dnsfail-" + hostname)

        # Convert actions into a dictionary { "what" : count }
        action_counts = {}
        for action in actions:
            action_counts.setdefault(action, 0)
            action_counts[action] += 1

        return action_counts

    def _core_is_running(self):
        if config.monitoring_core == "nagios":
            command = cmk.utils.paths.nagios_startscript + " status >/dev/null 2>&1"
        else:
            command = "omd status cmc >/dev/null 2>&1"
        code = os.system(command)  # nosec
        return not code

    def _rename_host_autochecks(self, oldname, newname):
        actions = []
        acpath = cmk.utils.paths.autochecks_dir + "/" + oldname + ".mk"
        if os.path.exists(acpath):
            old_autochecks = discovery.parse_autochecks_file(oldname)
            out = file(cmk.utils.paths.autochecks_dir + "/" + newname + ".mk", "w")
            out.write("[\n")
            for ct, item, paramstring in old_autochecks:
                out.write("  (%r, %r, %s),\n" % (ct, item, paramstring))
            out.write("]\n")
            out.close()
            os.remove(acpath)  # Remove old file
            actions.append("autochecks")
        return actions

    def _rename_host_files(self, oldname, newname):
        actions = []

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

    def _rename_host_dir(self, basedir, oldname, newname):
        if os.path.exists(basedir + "/" + oldname):
            if os.path.exists(basedir + "/" + newname):
                shutil.rmtree(basedir + "/" + newname)
            os.rename(basedir + "/" + oldname, basedir + "/" + newname)
            return 1
        return 0

    def _rename_host_file(self, basedir, oldname, newname):
        if os.path.exists(basedir + "/" + oldname):
            if os.path.exists(basedir + "/" + newname):
                os.remove(basedir + "/" + newname)
            os.rename(basedir + "/" + oldname, basedir + "/" + newname)
            return 1
        return 0

    # This functions could be moved out of Check_MK.
    def _omd_rename_host(self, oldname, newname):
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
            if self.rename_host_in_files(
                    os.path.join(cmk.utils.paths.omd_root, "var/rrdcached/rrd.journal.*"),
                    "/(perfdata|rrd)/%s/" % oldregex,
                    "/\\1/%s/" % newname,
                    extended_regex=True):
                actions.append("rrdcached")

            # Spoolfiles of NPCD
            if self.rename_host_in_files("%s/var/pnp4nagios/perfdata.dump" % cmk.utils.paths.omd_root,
                                 "HOSTNAME::%s    " % oldregex,
                                 "HOSTNAME::%s    " % newname) or \
               self.rename_host_in_files("%s/var/pnp4nagios/spool/perfdata.*" % cmk.utils.paths.omd_root,
                                 "HOSTNAME::%s    " % oldregex,
                                 "HOSTNAME::%s    " % newname):
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
                    "%s/var/nagios/retention.dat" % cmk.utils.paths.omd_root,
                    "^host_name=%s$" % oldregex,
                    "host_name=%s" % newname,
                    extended_regex=True):
                actions.append("retention")

        else:  # CMC
            # Create a file "renamed_hosts" with the information about the
            # renaming of the hosts. The core will honor this file when it
            # reads the status file with the saved state.
            file(cmk.utils.paths.var_dir + "/core/renamed_hosts",
                 "w").write("%s\n%s\n" % (oldname, newname))
            actions.append("retention")

        # NagVis maps
        if self.rename_host_in_files(
                "%s/etc/nagvis/maps/*.cfg" % cmk.utils.paths.omd_root,
                "^[[:space:]]*host_name=%s[[:space:]]*$" % oldregex,
                "host_name=%s" % newname,
                extended_regex=True):
            actions.append("nagvis")

        return actions

    def _rename_host_in_remaining_core_history_files(self, oldname, newname):
        """Perform the rename operation in all history archive files that have not been handled yet"""
        finished_file_paths = self._finished_history_files[(oldname, newname)]
        all_file_paths = set(self._get_core_history_files(only_archive=False))
        todo_file_paths = list(all_file_paths.difference(finished_file_paths))
        return self._rename_host_in_core_history_files(todo_file_paths, oldname, newname)

    def _rename_host_in_core_history_archive(self, oldname, newname):
        """Perform the rename operation in all history archive files"""
        file_paths = self._get_core_history_files(only_archive=True)
        return self._rename_host_in_core_history_files(file_paths, oldname, newname)

    def _get_core_history_files(self, only_archive):
        path_patterns = [
            "var/check_mk/core/archive/*",
            "var/nagios/archive/*",
        ]

        if not only_archive:
            path_patterns += [
                "var/check_mk/core/history",
                "var/nagios/nagios.log",
            ]

        file_paths = []
        for path_pattern in path_patterns:
            file_paths += glob.glob("%s/%s" % (cmk.utils.paths.omd_root, path_pattern))
        return file_paths

    def _rename_host_in_core_history_files(self, file_paths, oldname, newname):
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

        handled_files = []

        command = ["sed", "-ri", "--file=/dev/fd/0"]
        p = subprocess.Popen(
            command + file_paths,
            stdin=subprocess.PIPE,
            stdout=open(os.devnull, "w"),
            stderr=subprocess.STDOUT,
            close_fds=True)
        p.communicate(sed_commands)
        # TODO: error handling?

        handled_files += file_paths

        return handled_files

    # Returns True in case files were found, otherwise False
    def rename_host_in_files(self, path_pattern, old, new, extended_regex=False):
        paths = glob.glob(path_pattern)
        if paths:
            extended = ["-r"] if extended_regex else []
            subprocess.call(
                ["sed", "-i"] + extended + ["s@%s@%s@" % (old, new)] + paths,
                stderr=open(os.devnull, "w"))
            return True

        return False

    def _escape_name_for_regex_matching(self, name):
        return name.replace(".", "[.]")


automations.register(AutomationRenameHosts())


class AutomationAnalyseServices(Automation):
    cmd = "analyse-service"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args):
        hostname = args[0]
        servicedesc = args[1].decode("utf-8")

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
    def _get_service_info(self, config_cache, host_config, servicedesc):
        hostname = host_config.hostname
        check_api_utils.set_hostname(hostname)

        # We just consider types of checks that are managed via WATO.
        # We have the following possible types of services:
        # 1. manual checks (static_checks) (currently overriding inventorized checks)
        # 2. inventorized check
        # 3. classical checks
        # 4. active checks

        # Compute effective check table, in order to remove SNMP duplicates
        table = check_table.get_check_table(hostname, remove_duplicates=True)

        # 1. Manual checks
        for checkgroup_name, checktype, item, params in host_config.static_checks:
            descr = config.service_description(hostname, checktype, item)
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
            autochecks = []
            for node in host_config.nodes:
                for check_plugin_name, item, paramstring in cmk_base.autochecks.read_autochecks_of(
                        node):
                    descr = config.service_description(node, check_plugin_name, item)
                    if hostname == config_cache.host_of_clustered_service(node, descr):
                        autochecks.append((check_plugin_name, item, paramstring))
        else:
            autochecks = cmk_base.autochecks.read_autochecks_of(hostname)

        # 2. Load all autochecks of the host in question and try to find
        # our service there
        for entry in autochecks:
            ct, item, params = entry  # new format without host name

            if (ct, item) not in table:
                continue  # this is a removed duplicate or clustered service

            descr = config.service_description(hostname, ct, item)
            if descr == servicedesc:
                dlv = config.check_info[ct].get("default_levels_variable")
                if dlv:
                    fs = config.factory_settings.get(dlv, None)
                else:
                    fs = None

                check_parameters = config.compute_check_parameters(hostname, ct, item, params)
                if isinstance(check_parameters, cmk_base.config.TimespecificParamList):
                    check_parameters = cmk_base.checking.determine_check_params(check_parameters)
                    check_parameters = {
                        "tp_computed_params": {
                            "params": check_parameters,
                            "computed_at": time.time()
                        }
                    }

                return {
                    "origin": "auto",
                    "checktype": ct,
                    "checkgroup": config.check_info[ct].get("group"),
                    "item": item,
                    "inv_parameters": params,
                    "factory_settings": fs,
                    "parameters": check_parameters,
                }

        # 3. Classical checks
        for nr, entry in enumerate(host_config.custom_checks):
            desc = entry["service_description"]
            if desc == servicedesc:
                result = {
                    "origin": "classic",
                    "rule_nr": nr,
                }
                if "command_line" in entry:  # Only active checks have a command line
                    result["command_line"] = entry["command_line"]
                return result

        # 4. Active checks
        for plugin_name, entries in host_config.active_checks:
            for params in entries:
                description = config.active_check_service_description(hostname, plugin_name, params)
                if description == servicedesc:
                    return {
                        "origin": "active",
                        "checktype": plugin_name,
                        "parameters": params,
                    }

        return {}  # not found


automations.register(AutomationAnalyseServices())


class AutomationAnalyseHost(Automation):
    cmd = "analyse-host"
    needs_config = True
    needs_checks = False

    def execute(self, args):
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

    def execute(self, args):
        for hostname in args:
            self._delete_host_files(hostname)
        return None

    def _delete_host_files(self, hostname):
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

        return None

    def _delete_if_exists(self, path):
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

    def _mode(self):
        if config.monitoring_core == "cmc" and not self._check_plugins_have_changed():
            return "reload"  # force reload for cmc
        return "restart"

    # TODO: Cleanup duplicate code with cmk_base.core.do_restart()
    def execute(self, args):
        # make sure, Nagios does not inherit any open
        # filedescriptors. This really happens, e.g. if
        # check_mk is called by WATO via Apache. Nagios inherits
        # the open file where Apache is listening for incoming
        # HTTP connections. Really.
        if config.monitoring_core == "nagios":
            objects_file = cmk.utils.paths.nagios_objects_file
            cmk.utils.daemon.closefrom(3)
        else:
            objects_file = cmk.utils.paths.var_dir + "/core/config"

        class null_file(object):
            def write(self, stuff):
                pass

            def flush(self):
                pass

        # Deactivate stdout by introducing fake file without filedescriptor
        old_stdout = sys.stdout
        sys.stdout = null_file()

        try:
            backup_path = None
            if cmk_base.core.try_get_activation_lock():
                raise MKAutomationError("Cannot activate changes. "
                                        "Another activation process is currently in progresss")

            if os.path.exists(objects_file):
                backup_path = objects_file + ".save"
                os.rename(objects_file, backup_path)
            else:
                backup_path = None

            core = create_core()
            try:
                configuration_warnings = core_config.create_core_config(core)

                try:
                    from cmk_base.cee.agent_bakery import bake_on_restart
                    bake_on_restart()
                except ImportError:
                    pass

            except Exception as e:
                if backup_path:
                    os.rename(backup_path, objects_file)
                if cmk.utils.debug.enabled():
                    raise
                raise MKAutomationError("Error creating configuration: %s" % e)

            if config.monitoring_core == "cmc" or cmk_base.nagios_utils.do_check_nagiosconfig():
                if backup_path:
                    os.remove(backup_path)

                core.precompile()

                cmk_base.core.do_core_action(self._mode())
            else:
                broken_config_path = "%s/check_mk_objects.cfg.broken" % cmk.utils.paths.tmp_dir
                file(broken_config_path, "w").write(
                    file(cmk.utils.paths.nagios_objects_file).read())

                if backup_path:
                    os.rename(backup_path, objects_file)
                else:
                    os.remove(objects_file)

                raise MKAutomationError(
                    "Configuration for monitoring core is invalid. Rolling back. "
                    "The broken file has been copied to \"%s\" for analysis." % broken_config_path)

        except Exception as e:
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
            if cmk.utils.debug.enabled():
                raise
            raise MKAutomationError(str(e))

        sys.stdout = old_stdout
        return configuration_warnings

    def _check_plugins_have_changed(self):
        this_time = self._last_modification_in_dir(cmk.utils.paths.local_checks_dir)
        last_time = self._time_of_last_core_restart()
        return this_time > last_time

    def _last_modification_in_dir(self, dir_path):
        max_time = os.stat(dir_path).st_mtime
        for file_name in os.listdir(dir_path):
            max_time = max(max_time, os.stat(dir_path + "/" + file_name).st_mtime)
        return max_time

    def _time_of_last_core_restart(self):
        if config.monitoring_core == "cmc":
            pidfile_path = cmk.utils.paths.omd_root + "/tmp/run/cmc.pid"
        else:
            pidfile_path = cmk.utils.paths.omd_root + "/tmp/lock/nagios.lock"

        if os.path.exists(pidfile_path):
            return os.stat(pidfile_path).st_mtime

        return 0


automations.register(AutomationRestart())


class AutomationReload(AutomationRestart):
    cmd = "reload"

    def _mode(self):
        if self._check_plugins_have_changed():
            return "restart"
        return "reload"


automations.register(AutomationReload())


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

    def execute(self, args):
        config.load(with_conf_d=False)

        # We read the list of variable names from stdin since
        # that could be too much for the command line
        variable_names = ast.literal_eval(sys.stdin.read())

        missing_variables = [v for v in variable_names if not hasattr(config, v)]

        if missing_variables:
            config.load_all_checks(check_api.get_check_api_context)
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

    def execute(self, args):
        manuals = man_pages.all_man_pages()

        check_infos = {}
        for check_plugin_name, check in config.check_info.items():
            try:
                manfile = manuals.get(check_plugin_name)
                # TODO: Use cmk.utils.man_pages module standard functions to read the title
                if manfile:
                    title = file(manfile).readline().strip().split(":", 1)[1].strip()
                else:
                    title = check_plugin_name
                check_infos[check_plugin_name] = {"title": title.decode("utf-8")}
                if check["group"]:
                    check_infos[check_plugin_name]["group"] = check["group"]
                check_infos[check_plugin_name]["service_description"] = check.get(
                    "service_description", "%s")
                check_infos[check_plugin_name]["snmp"] = cmk_base.check_utils.is_snmp_check(
                    check_plugin_name)
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                raise MKAutomationError(
                    "Failed to parse man page '%s': %s" % (check_plugin_name, e))
        return check_infos


automations.register(AutomationGetCheckInformation())


class AutomationGetRealTimeChecks(Automation):
    cmd = "get-real-time-checks"
    needs_config = False
    needs_checks = True

    def execute(self, args):
        manuals = man_pages.all_man_pages()

        rt_checks = []
        for check_plugin_name, check in config.check_info.items():
            if check["handle_real_time_checks"]:
                # TODO: Use cmk.utils.man_pages module standard functions to read the title
                title = check_plugin_name
                try:
                    manfile = manuals.get(check_plugin_name)
                    if manfile:
                        title = file(manfile).readline().strip().split(":", 1)[1].strip()
                except Exception:
                    if cmk.utils.debug.enabled():
                        raise

                rt_checks.append((check_plugin_name,
                                  "%s - %s" % (check_plugin_name, title.decode("utf-8"))))

        return rt_checks


automations.register(AutomationGetRealTimeChecks())


class AutomationGetCheckManPage(Automation):
    cmd = "get-check-manpage"
    needs_config = False
    needs_checks = True

    def execute(self, args):
        if len(args) != 1:
            raise MKAutomationError("Need exactly one argument.")

        check_plugin_name = args[0]
        manpage = man_pages.load_man_page(args[0])

        # Add a few informations from check_info. Note: active checks do not
        # have an entry in check_info
        if check_plugin_name in config.check_info:
            manpage["type"] = "check_mk"
            info = config.check_info[check_plugin_name]
            for key in ["snmp_info", "has_perfdata", "service_description"]:
                if key in info:
                    manpage[key] = info[key]
            if "." in check_plugin_name:
                section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
                if section_name in config.check_info and "snmp_info" in config.check_info[
                        section_name]:
                    manpage["snmp_info"] = config.check_info[section_name]["snmp_info"]

            if "group" in info:
                manpage["group"] = info["group"]

        # Assume active check
        elif check_plugin_name.startswith("check_"):
            manpage["type"] = "active"
        else:
            raise MKAutomationError("Could not detect type of manpage: %s. "
                                    "Maybe the check is missing." % check_plugin_name)

        return manpage


automations.register(AutomationGetCheckManPage())


class AutomationScanParents(Automation):
    cmd = "scan-parents"
    needs_config = True
    needs_checks = True

    def execute(self, args):
        settings = {
            "timeout": int(args[0]),
            "probes": int(args[1]),
            "max_ttl": int(args[2]),
            "ping_probes": int(args[3]),
        }
        hostnames = args[4:]
        if not cmk_base.parent_scan.traceroute_available():
            raise MKAutomationError("Cannot find binary <tt>traceroute</tt> in search path.")
        config_cache = config.get_config_cache()

        try:
            gateways = cmk_base.parent_scan.scan_parents_of(
                config_cache, hostnames, silent=True, settings=settings)
            return gateways
        except Exception as e:
            raise MKAutomationError("%s" % e)


automations.register(AutomationScanParents())


class AutomationDiagHost(Automation):
    cmd = "diag-host"
    needs_config = True
    needs_checks = True

    def execute(self, args):
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
                ipaddress = ip_lookup.lookup_ip_address(hostname)
            except:
                raise MKGeneralException("Cannot resolve hostname %s into IP address" % hostname)

        snmp_config = host_config.snmp_config(ipaddress)

        try:
            if test == 'ping':
                base_cmd = "ping6" if host_config.is_ipv6_primary else "ping"
                p = subprocess.Popen([base_cmd, "-A", "-i", "0.2", "-c", "2", "-W", "5", ipaddress],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
                response = p.stdout.read()
                return (p.wait(), response)

            elif test == 'agent':
                sources = data_sources.DataSources(hostname, ipaddress)
                sources.set_max_cachefile_age(config.check_max_cachefile_age)

                output = ""
                for source in sources.get_data_sources():
                    if isinstance(source, data_sources.DSProgramDataSource) and cmd:
                        source = data_sources.DSProgramDataSource(hostname, ipaddress, cmd)
                    elif isinstance(source, data_sources.TCPDataSource):
                        source.set_port(agent_port)
                        if tcp_connect_timeout is not None:
                            source.set_timeout(tcp_connect_timeout)
                    elif isinstance(source, data_sources.snmp.SNMPDataSource):
                        continue

                    output += source.run_raw()
                    if source.exception():
                        output += "%s" % source.exception()

                return 0, output

            elif test == 'traceroute':
                family_flag = "-6" if host_config.is_ipv6_primary else "-4"
                try:
                    p = subprocess.Popen(['traceroute', family_flag, '-n', ipaddress],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        return 1, "Cannot find binary <tt>traceroute</tt>."
                    else:
                        raise
                response = p.stdout.read()
                return (p.wait(), response)

            elif test.startswith('snmp'):
                # SNMPv3 tuples
                # ('noAuthNoPriv', "username")
                # ('authNoPriv', 'md5', '11111111', '22222222')
                # ('authPriv', 'md5', '11111111', '22222222', 'DES', '33333333')

                credentials = snmp_config.credentials

                # Insert preconfigured communitiy
                if test == "snmpv3":
                    if snmpv3_use:
                        snmpv3_credentials = [snmpv3_use]
                        if snmpv3_use in ["authNoPriv", "authPriv"]:
                            snmpv3_credentials.extend(
                                [snmpv3_auth_proto, snmpv3_security_name, snmpv3_security_password])
                        else:
                            snmpv3_credentials.extend([snmpv3_security_name])
                        if snmpv3_use == "authPriv":
                            snmpv3_credentials.extend(
                                [snmpv3_privacy_proto, snmpv3_privacy_password])
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
                snmp_config = snmp_utils.SNMPHostConfig(
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
                )

                data = snmp.get_snmp_table(
                    snmp_config,
                    None, ('.1.3.6.1.2.1.1', ['1.0', '4.0', '5.0', '6.0']),
                    use_snmpwalk_cache=True)

                if data:
                    return 0, 'sysDescr:\t%s\nsysContact:\t%s\nsysName:\t%s\nsysLocation:\t%s\n' % tuple(
                        data[0])

                return 1, 'Got empty SNMP response'

            else:
                return 1, "Command not implemented"

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            return 1, str(e)


automations.register(AutomationDiagHost())


class AutomationActiveCheck(Automation):
    cmd = "active-check"
    needs_config = True
    needs_checks = True

    def execute(self, args):
        hostname, plugin, item = args
        item = item.decode("utf-8")

        host_config = config.get_config_cache().get_host_config(hostname)

        if plugin == "custom":
            for entry in host_config.custom_checks:
                if entry["service_description"] != item:
                    continue

                command_line = self._replace_core_macros(hostname, entry.get("command_line", ""))
                if command_line:
                    command_line = core_config.autodetect_plugin(command_line)
                    return self._execute_check_plugin(command_line)

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

            args = core_config.active_check_arguments(hostname, description,
                                                      act_info["argument_function"](params))
            command_line = self._replace_core_macros(
                hostname, act_info["command_line"].replace("$ARG1$", args))
            return self._execute_check_plugin(command_line)

    def _load_resource_file(self, macros):
        try:
            for line in file(cmk.utils.paths.omd_root + "/etc/nagios/resource.cfg"):
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
    def _replace_core_macros(self, hostname, commandline):
        config_cache = config.get_config_cache()
        macros = core_config.get_host_macros_from_attributes(
            hostname, core_config.get_host_attributes(hostname, config_cache))
        self._load_resource_file(macros)
        for varname, value in macros.items():
            commandline = commandline.replace(varname, "%s" % value)
        return commandline

    def _execute_check_plugin(self, commandline):
        try:
            p = os.popen(commandline + " 2>&1")  # nosec
            output = p.read().strip()
            ret = p.close()
            if not ret:
                status = 0
            else:
                if ret & 0xff == 0:
                    status = ret / 256
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

    def execute(self, args):
        return ip_lookup.update_dns_cache()


automations.register(AutomationUpdateDNSCache())


class AutomationGetAgentOutput(Automation):
    cmd = "get-agent-output"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args):
        hostname, ty = args

        success = True
        output = ""
        info = ""

        try:
            if ty == "agent":
                data_sources.abstract.DataSource.set_may_use_cache_file(
                    not data_sources.abstract.DataSource.is_agent_cache_disabled())

                ipaddress = ip_lookup.lookup_ip_address(hostname)
                sources = data_sources.DataSources(hostname, ipaddress)
                sources.set_max_cachefile_age(config.check_max_cachefile_age)

                agent_output = ""
                for source in sources.get_data_sources():
                    if isinstance(source, data_sources.abstract.CheckMKAgentDataSource):
                        agent_output += source.run(hostname, ipaddress, get_raw_data=True)
                info = agent_output

                # Optionally show errors of problematic data sources
                for source in sources.get_data_sources():
                    source_state, source_output, _source_perfdata = source.get_summary_result_for_checking(
                    )
                    if source_state != 0:
                        success = False
                        output += "[%s] %s\n" % (source.id(), source_output)
            else:
                host_config = snmp.create_snmp_host_config(hostname)

                lines = []
                for walk_oid in snmp.oids_to_walk():
                    try:
                        for oid, value in snmp.walk_for_export(host_config, walk_oid):
                            lines.append("%s %s\n" % (oid, value))
                    except Exception as e:
                        if cmk.utils.debug.enabled():
                            raise
                        success = False
                        output += "OID '%s': %s\n" % (oid, e)

                info = "".join(lines)
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

    def execute(self, args):
        nr = args[0]
        return notify.notification_replay_backlog(int(nr))


automations.register(AutomationNotificationReplay())


class AutomationNotificationAnalyse(Automation):
    cmd = "notification-analyse"
    needs_config = True
    needs_checks = True  # TODO: Can we change this?

    def execute(self, args):
        nr = args[0]
        return notify.notification_analyse_backlog(int(nr))


automations.register(AutomationNotificationAnalyse())


class AutomationGetBulks(Automation):
    cmd = "notification-get-bulks"
    needs_config = False
    needs_checks = False

    def execute(self, args):
        only_ripe = args[0] == "1"
        return notify.find_bulks(only_ripe)


automations.register(AutomationGetBulks())


class AutomationGetServiceConfigurations(Automation):
    cmd = "get-service-configurations"
    needs_config = True
    needs_checks = True

    def execute(self, args):
        result = {"hosts": {}}
        config_cache = config.get_config_cache()
        for hostname in config_cache.all_active_hosts():
            host_config = config_cache.get_host_config(hostname)
            result["hosts"][hostname] = self._get_config_for_host(host_config)

        result["checkgroup_of_checks"] = self._get_checkgroup_of_checks()
        return result

    def _get_config_for_host(self, host_config):
        # type: (config.HostConfig) -> Dict[str, List[Tuple[str, Text, Any]]]
        return {
            "checks": check_table.get_check_table(host_config.hostname, remove_duplicates=True),
            "active_checks": self._get_active_checks(host_config)
        }

    def _get_active_checks(self, host_config):
        # type: (config.HostConfig) -> List[Tuple[str, Text, Any]]
        actchecks = []
        for plugin_name, entries in host_config.active_checks:
            for params in entries:
                description = config.active_check_service_description(host_config.hostname,
                                                                      plugin_name, params)
                actchecks.append((plugin_name, description, params))
        return actchecks

    def _get_checkgroup_of_checks(self):
        # type: () -> Dict[str, Optional[str]]
        checkgroup_of_checks = {}
        for check_plugin_name, check in config.check_info.items():
            checkgroup_of_checks[check_plugin_name] = check.get("group")
        return checkgroup_of_checks


automations.register(AutomationGetServiceConfigurations())


class AutomationGetLabelsOf(Automation):
    cmd = "get-labels-of"
    needs_config = True
    needs_checks = False

    def execute(self, args):
        object_type, host_name = args[:2]

        config_cache = config.get_config_cache()

        if object_type == "host":
            return {
                "labels": config_cache.get_host_config(host_name).labels,
                "label_sources": config_cache.get_host_config(host_name).label_sources,
            }

        if object_type == "service":
            service_description = args[2].decode("utf-8")
            return {
                "labels": config_cache.labels_of_service(host_name, service_description),
                "label_sources": config_cache.label_sources_of_service(
                    host_name, service_description),
            }

        raise NotImplementedError()


automations.register(AutomationGetLabelsOf())
