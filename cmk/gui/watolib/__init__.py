#!/usr/bin/python
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

# WATO LIBRARY
#
# This file contains classes, functions and globals that are being
# used by WATO. It does not contain any acutal page handlers or
# WATO modes. Nor complex HTML creation. This is all contained
# in wato.py

#   .--Initialization------------------------------------------------------.
#   |                           ___       _ _                              |
#   |                          |_ _|_ __ (_) |_                            |
#   |                           | || '_ \| | __|                           |
#   |                           | || | | | | |_                            |
#   |                          |___|_| |_|_|\__|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Doing this that must be done when the module WATO is loaded.        |
#   '----------------------------------------------------------------------'

import abc
import ast
import base64
import cStringIO
import copy
import glob
from hashlib import sha256
import multiprocessing
import os
import pickle
import pprint
import pwd
import re
import shutil
import signal
import socket
import subprocess
import tarfile
import threading
import time
import traceback
from typing import NamedTuple, List  # pylint: disable=unused-import

import requests
from pathlib2 import Path
import six

import cmk
import cmk.utils.daemon as daemon
import cmk.utils.paths
import cmk.utils.defines
import cmk.utils
import cmk.utils.store as store
import cmk.utils.render as render
import cmk.ec.defaults
import cmk.ec.export
import cmk.utils.regex
import cmk.utils.plugin_registry

import cmk.gui.utils
import cmk.gui.sites
import cmk.gui.config as config
import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
import cmk.gui.multitar as multitar
import cmk.gui.mkeventd as mkeventd
import cmk.gui.log as log
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.weblib as weblib
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML, Encoder
from cmk.gui.log import logger
from cmk.gui.exceptions import MKGeneralException, MKAuthException, MKUserError, RequestTimeout
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    HostAddress,
    ListOfStrings,
    IPNetwork,
    Checkbox,
    Transform,
    DropdownChoice,
    ListOf,
    EmailAddressUnicode,
    DualListChoice,
    UserID,
    FixedValue,
    Alternative,
    CascadingDropdown,
    TextAscii,
    TextUnicode,
    TextAreaUnicode,
    TextAsciiAutocomplete,
    ValueSpec,
    ListChoice,
    Float,
    Foldable,
    Tuple,
    Age,
    RegExp,
    MonitoredHostname,
)

import cmk.gui.watolib.timeperiods
import cmk.gui.watolib.git
import cmk.gui.watolib.changes
# TODO: Cleanup all except declare_host_attribute which is still neded for pre 1.6 plugin
# compatibility. For the others: Find the call sites and change to full module import
from cmk.gui.watolib.notifications import save_notification_rules
from cmk.gui.watolib.timeperiods import TimeperiodSelection
from cmk.gui.watolib.host_attributes import (
    all_host_attributes,
    declare_host_attribute,
    undeclare_host_attribute,
    host_attribute,
    collect_attributes,
)
from cmk.gui.watolib.automations import (
    MKAutomationException,
    do_remote_automation,
    check_mk_automation,
    check_mk_local_automation,
    get_url,
)
from cmk.gui.watolib.config_domains import (
    ConfigDomainCore,
    ConfigDomainGUI,
    ConfigDomainLiveproxy,
)
from cmk.gui.watolib.sites import (
    SiteManagementFactory,
    CEESiteManagement,
    LivestatusViaTCP,
    sites_mk,
    create_distributed_wato_file,
)
from cmk.gui.watolib.changes import (
    log_entry,
    log_audit,
    add_change,
    ActivateChanges,
    ActivateChangesManager,
    ActivateChangesSite,
    add_replication_paths,
    get_replication_paths,
    confirm_all_local_changes,
    get_pending_changes_info,
    get_number_of_pending_changes,
)
from cmk.gui.watolib.groups import (
    edit_group,
    add_group,
    delete_group,
    save_group_information,
    find_usages_of_group,
    is_alias_used,
)
from cmk.gui.watolib.rulespecs import (
    RulespecGroup,
    RulespecSubGroup,
    RulespecGroupRegistry,
    rulespec_group_registry,
    RulespecGroupStaticChecks,
    register_rulegroup,
    get_rulegroup,
    Rulespecs,
    g_rulespecs,
    Rulespec,
    register_rule,
)
from cmk.gui.watolib.rulesets import (
    RulesetCollection,
    AllRulesets,
    SingleRulesetRecursively,
    FolderRulesets,
    FilteredRulesetCollection,
    StaticChecksRulesets,
    NonStaticChecksRulesets,
    SearchedRulesets,
    Ruleset,
    Rule,
)
from cmk.gui.watolib.host_tags import (
    parse_hosttag_title,
    is_builtin_host_tag_group,
    group_hosttags_by_topic,
    Hosttag,
    AuxTag,
    AuxtagList,
    BuiltinAuxtagList,
    GroupedHosttag,
    HosttagGroup,
    HosttagsConfiguration,
    BuiltinHosttagsConfiguration,
    save_hosttags,
)
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    Host,
    validate_all_hosts,
    call_hook_hosts_changed,
    folder_preserving_link,
)
from cmk.gui.watolib.sidebar_reload import (
    is_sidebar_reload_needed,
    need_sidebar_reload,
)
from cmk.gui.watolib.analyze_configuration import (
    ACResultNone,
    ACResultCRIT,
    ACResultWARN,
    ACResultOK,
    ACTestCategories,
    ACTest,
    ac_test_registry,
)
from cmk.gui.watolib.snapshots import backup_domains
from cmk.gui.watolib.automation_commands import (AutomationCommand, automation_command_registry)
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.utils import (
    ALL_HOSTS,
    ALL_SERVICES,
    NEGATE,
    NO_ITEM,
    ENTRY_NEGATE_CHAR,
    wato_root_dir,
    multisite_dir,
    rename_host_in_list,
    convert_cgroups_from_tuple,
    host_attribute_matches,
    default_site,
    format_config_value,
    liveproxyd_config_dir,
    lock_exclusive,
    mk_repr,
    exclusive_lock,
    has_agent_bakery,
)

if cmk.is_managed_edition():
    import cmk.gui.cme.managed as managed

from cmk.gui.plugins.watolib.utils import (
    ConfigDomain,
    config_domain_registry,
    config_variable_registry,
    wato_fileheader,
)

import cmk.gui.plugins.watolib

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.watolib


def load_watolib_plugins():
    cmk.gui.utils.load_web_plugins("watolib", globals())


# TODO: Must only be unlocked when it was not locked before. We should find a more
# robust way for doing something like this. If it is locked before, it can now happen
# that this call unlocks the wider locking when calling this funktion in a wrong way.
def init_wato_datastructures(with_wato_lock=False):
    init_watolib_datastructures()
    if os.path.exists(ConfigDomainCACertificates.trusted_cas_file) and\
        not _need_to_create_sample_config():
        return

    def init():
        if not os.path.exists(ConfigDomainCACertificates.trusted_cas_file):
            ConfigDomainCACertificates().activate()
        _create_sample_config()

    if with_wato_lock:
        with exclusive_lock():
            init()
    else:
        init()


# TODO: Create a hook here and move CEE and other specific things away
def _create_sample_config():
    """Create a very basic sample configuration

    But only if none of the
    files that we will create already exists. That is e.g. the case
    after an update from an older version where no sample config had
    been created.
    """
    if not _need_to_create_sample_config():
        return

    # Just in case. If any of the following functions try to write Git messages
    if config.wato_use_git:
        cmk.gui.watolib.git.prepare_git_commit()

    # Global configuration settings
    save_global_settings({
        "use_new_descriptions_for": [
            "df",
            "df_netapp",
            "df_netapp32",
            "esx_vsphere_datastores",
            "hr_fs",
            "vms_diskstat.df",
            "zfsget",
            "ps",
            "ps.perf",
            "wmic_process",
            "services",
            "logwatch",
            "logwatch.groups",
            "cmk-inventory",
            "hyperv_vms",
            "ibm_svc_mdiskgrp",
            "ibm_svc_system",
            "ibm_svc_systemstats.diskio",
            "ibm_svc_systemstats.iops",
            "ibm_svc_systemstats.disk_latency",
            "ibm_svc_systemstats.cache",
            "casa_cpu_temp",
            "cmciii.temp",
            "cmciii.psm_current",
            "cmciii_lcp_airin",
            "cmciii_lcp_airout",
            "cmciii_lcp_water",
            "etherbox.temp",
            "liebert_bat_temp",
            "nvidia.temp",
            "ups_bat_temp",
            "innovaphone_temp",
            "enterasys_temp",
            "raritan_emx",
            "raritan_pdu_inlet",
            "mknotifyd",
            "mknotifyd.connection",
            "postfix_mailq",
            "nullmailer_mailq",
            "barracuda_mailqueues",
            "qmail_stats",
            "http",
            "mssql_backup",
            "mssql_counters.cache_hits",
            "mssql_counters.transactions",
            "mssql_counters.locks",
            "mssql_counters.sqlstats",
            "mssql_counters.pageactivity",
            "mssql_counters.locks_per_batch",
            "mssql_counters.file_sizes",
            "mssql_databases",
            "mssql_datafiles",
            "mssql_tablespaces",
            "mssql_transactionlogs",
            "mssql_versions",
        ],
        "enable_rulebased_notifications": True,
        "ui_theme": "facelift",
    })

    # A contact group for all hosts and services
    groups = {
        "contact": {
            'all': {
                'alias': u'Everything'
            }
        },
    }
    save_group_information(groups)

    # Basic setting of host tags
    wato_host_tags = \
    [('criticality',
      u'Criticality',
      [('prod', u'Productive system', []),
       ('critical', u'Business critical', []),
       ('test', u'Test system', []),
       ('offline', u'Do not monitor this host', [])]),
     ('networking',
      u'Networking Segment',
      [('lan', u'Local network (low latency)', []),
       ('wan', u'WAN (high latency)', []),
       ('dmz', u'DMZ (low latency, secure access)', [])]),
    ]

    wato_aux_tags = []

    save_hosttags(wato_host_tags, wato_aux_tags)

    # Rules that match the upper host tag definition
    ruleset_config = {
        # Make the tag 'offline' remove hosts from the monitoring
        'only_hosts': [(['!offline'], ['@all'], {
            'description': u'Do not monitor hosts with the tag "offline"'
        }),],

        # Rule for WAN hosts with adapted PING levels
        'ping_levels': [({
            'loss': (80.0, 100.0),
            'packets': 6,
            'rta': (1500.0, 3000.0),
            'timeout': 20
        }, ['wan'], ['@all'], {
            'description': u'Allow longer round trip times when pinging WAN hosts'
        }),],

        # All hosts should use SNMP v2c if not specially tagged
        'bulkwalk_hosts': [(['snmp', '!snmp-v1'], ['@all'], {
            'description': u'Hosts with the tag "snmp-v1" must not use bulkwalk'
        }),],

        # Put all hosts and the contact group 'all'
        'host_contactgroups': [('all', [], ALL_HOSTS, {
            'description': u'Put all hosts into the contact group "all"'
        }),],

        # Interval for HW/SW-Inventory check
        'extra_service_conf': {
            'check_interval': [(1440, [], ALL_HOSTS, ["Check_MK HW/SW Inventory$"], {
                'description': u'Restrict HW/SW-Inventory to once a day'
            }),],
        },

        # Disable unreachable notifications by default
        'extra_host_conf': {
            'notification_options': [('d,r,f,s', [], ALL_HOSTS, {}),],
        },

        # Periodic service discovery
        'periodic_discovery': [({
            'severity_unmonitored': 1,
            'severity_vanished': 0,
            'inventory_check_do_scan': True,
            'check_interval': 120.0
        }, [], ALL_HOSTS, {
            'description': u'Perform every two hours a service discovery'
        }),],
    }

    rulesets = FolderRulesets(Folder.root_folder())
    rulesets.from_config(Folder.root_folder(), ruleset_config)
    rulesets.save()

    notification_rules = [
        {
            'allow_disable': True,
            'contact_all': False,
            'contact_all_with_email': False,
            'contact_object': True,
            'description': 'Notify all contacts of a host/service via HTML email',
            'disabled': False,
            'notify_plugin': ('mail', {}),
        },
    ]
    save_notification_rules(notification_rules)

    try:
        import cmk.gui.cee.plugins.wato.sample_config
        cmk.gui.cee.plugins.wato.sample_config.create_cee_sample_config()
    except ImportError:
        pass

    # Make sure the host tag attributes are immediately declared!
    config.wato_host_tags = wato_host_tags
    config.wato_aux_tags = wato_aux_tags

    # Initial baking of agents (when bakery is available)
    if has_agent_bakery():
        import cmk.gui.cee.plugins.wato.agent_bakery
        bake_job = cmk.gui.cee.plugins.wato.agent_bakery.BakeAgentsBackgroundJob()
        bake_job.set_function(cmk.gui.cee.plugins.wato.agent_bakery.bake_agents_background_job)
        try:
            bake_job.start()
        except background_job.BackgroundJobAlreadyRunning:
            pass

    # This is not really the correct place for such kind of action, but the best place we could
    # find to execute it only for new created sites.
    import cmk.gui.werks as werks
    werks.acknowledge_all_werks(check_permission=False)

    cmk.gui.wato.mkeventd.save_mkeventd_sample_config()

    userdb.create_cmk_automation_user()


def _need_to_create_sample_config():
    if os.path.exists(multisite_dir + "hosttags.mk") \
        or os.path.exists(wato_root_dir + "rules.mk") \
        or os.path.exists(wato_root_dir + "groups.mk") \
        or os.path.exists(wato_root_dir + "notifications.mk") \
        or os.path.exists(wato_root_dir + "global.mk"):
        return False
    return True


def init_watolib_datastructures():
    if config.wato_use_git:
        cmk.gui.watolib.git.prepare_git_commit()

    cmk.gui.watolib.sidebar_reload.reset()
    update_config_based_host_attributes()


#
# NEW sync code
#


def add_service_change(host, action_name, text, need_sync=False):
    add_change(action_name, text, obj=host, sites=[host.site_id()], need_sync=need_sync)


@config_domain_registry.register
class ConfigDomainEventConsole(ConfigDomain):
    needs_sync = True
    needs_activation = True
    ident = "ec"
    in_global_settings = False

    @classmethod
    def enabled(cls):
        return config.mkeventd_enabled

    def config_dir(self):
        return str(cmk.ec.export.rule_pack_dir())

    def activate(self):
        if getattr(config, "mkeventd_enabled", False):
            mkeventd.execute_command("RELOAD", site=config.omd_site())
            log_audit(None, "mkeventd-activate",
                      _("Activated changes of event console configuration"))
            if hooks.registered('mkeventd-activate-changes'):
                hooks.call("mkeventd-activate-changes")

    def default_globals(self):
        return cmk.ec.defaults.default_config()


@config_domain_registry.register
class ConfigDomainCACertificates(ConfigDomain):
    needs_sync = True
    needs_activation = True
    always_activate = True  # Execute this on all sites on all activations
    ident = "ca-certificates"

    trusted_cas_file = "%s/var/ssl/ca-certificates.crt" % cmk.utils.paths.omd_root

    # This is a list of directories that may contain .pem files of trusted CAs.
    # The contents of all .pem files will be contantenated together and written
    # to "trusted_cas_file". This is done by the function update_trusted_cas().
    # On a system only a single directory, the first existing one is processed.
    system_wide_trusted_ca_search_paths = [
        "/etc/ssl/certs",  # Ubuntu/Debian/SLES
        "/etc/pki/tls/certs",  # CentOS/RedHat
    ]

    _PEM_RE = re.compile(b"-----BEGIN CERTIFICATE-----\r?.+?\r?-----END CERTIFICATE-----\r?\n?"
                         "", re.DOTALL)

    def config_dir(self):
        return multisite_dir

    def config_file(self, site_specific=False):
        return os.path.join(self.config_dir(), "ca-certificates.mk")

    def save(self, settings, site_specific=False):
        super(ConfigDomainCACertificates, self).save(settings, site_specific=site_specific)

        current_config = settings.get("trusted_certificate_authorities", {
            "use_system_wide_cas": True,
            "trusted_cas": [],
        })

        # We need to activate this immediately to make syncs to WATO slave sites
        # possible right after changing the option
        #
        # Since this can be called from any WATO page it is not possible to report
        # errors to the user here. The self._update_trusted_cas() method logs the
        # errors - this must be enough for the moment.
        self._update_trusted_cas(current_config)

    def activate(self):
        try:
            return self._update_trusted_cas(config.trusted_certificate_authorities)
        except Exception:
            logger.exception()
            return [
                "Failed to create trusted CA file '%s': %s" % (self.trusted_cas_file,
                                                               traceback.format_exc())
            ]

    def _update_trusted_cas(self, current_config):
        trusted_cas, errors = [], []

        if current_config["use_system_wide_cas"]:
            trusted, errors = self._get_system_wide_trusted_ca_certificates()
            trusted_cas += trusted

        trusted_cas += current_config["trusted_cas"]

        store.save_file(self.trusted_cas_file, "\n".join(trusted_cas))
        return errors

    def _get_system_wide_trusted_ca_certificates(self):
        trusted_cas, errors = set([]), []
        for p in self.system_wide_trusted_ca_search_paths:
            cert_path = Path(p)

            if not cert_path.is_dir():
                continue

            for entry in cert_path.iterdir():
                cert_file_path = entry.absolute()
                try:
                    if entry.suffix not in [".pem", ".crt"]:
                        continue

                    trusted_cas.update(self._get_certificates_from_file(cert_file_path))
                except IOError:
                    logger.exception()

                    # This error is shown to the user as warning message during "activate changes".
                    # We keep this message for the moment because we think that it is a helpful
                    # trigger for further checking web.log when a really needed certificate can
                    # not be read.
                    #
                    # We know a permission problem with some files that are created by default on
                    # some distros. We simply ignore these files because we assume that they are
                    # not needed.
                    if cert_file_path == Path("/etc/ssl/certs/localhost.crt"):
                        continue

                    errors.append("Failed to add certificate '%s' to trusted CA certificates. "
                                  "See web.log for details." % cert_file_path)

            break

        return list(trusted_cas), errors

    def _get_certificates_from_file(self, path):
        try:
            return [match.group(0) for match in self._PEM_RE.finditer(open("%s" % path).read())]
        except IOError as e:
            if e.errno == 2:  # No such file or directory
                # Silently ignore e.g. dangling symlinks
                return []
            else:
                raise

    def default_globals(self):
        return {
            "trusted_certificate_authorities": {
                "use_system_wide_cas": True,
                "trusted_cas": [],
            }
        }


@config_domain_registry.register
class ConfigDomainOMD(ConfigDomain):
    needs_sync = True
    needs_activation = True
    ident = "omd"
    omd_config_dir = "%s/etc/omd" % (cmk.utils.paths.omd_root)

    def __init__(self):
        super(ConfigDomainOMD, self).__init__()
        self._logger = logger.getChild("config.omd")

    def config_dir(self):
        return self.omd_config_dir

    def default_globals(self):
        return self._from_omd_config(self._load_site_config())

    def activate(self):
        current_settings = self._load_site_config()

        settings = {}
        settings.update(self._to_omd_config(self.load()))
        settings.update(self._to_omd_config(self.load_site_globals()))

        config_change_commands = []
        self._logger.debug("Set omd config: %r" % settings)

        for key, val in settings.items():
            if key not in current_settings:
                continue  # Skip settings unknown to current OMD

            if current_settings[key] == settings[key]:
                continue  # Skip unchanged settings

            config_change_commands.append("%s=%s" % (key, val))

        if not config_change_commands:
            self._logger.debug("Got no config change commands...")
            return

        self._logger.debug("Executing \"omd config change\"")
        self._logger.debug("  Commands: %r" % config_change_commands)
        p = subprocess.Popen(["omd", "config", "change"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE,
                             close_fds=True)
        stdout = p.communicate(cmk.utils.make_utf8("\n".join(config_change_commands)))[0]
        self._logger.debug("  Exit code: %d" % p.returncode)
        self._logger.debug("  Output: %r" % stdout)
        if p.returncode != 0:
            raise MKGeneralException(
                _("Failed to activate changed site "
                  "configuration.\nExit code: %d\nConfig: %s\nOutput: %s") %
                (p.returncode, config_change_commands, stdout))

    def _load_site_config(self):
        return self._load_omd_config("%s/site.conf" % self.omd_config_dir)

    def _load_omd_config(self, path):
        settings = {}

        if not os.path.exists(path):
            return {}

        try:
            for line in file(path):
                line = line.strip()

                if line == "" or line.startswith("#"):
                    continue

                var, value = line.split("=", 1)

                if not var.startswith("CONFIG_"):
                    continue

                key = var[7:].strip()
                val = value.strip().strip("'")

                settings[key] = val
        except Exception as e:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") % (path, e))

        return settings

    # Convert the raw OMD configuration settings to the WATO config format.
    # The format that is understood by the valuespecs. Since some valuespecs
    # affect multiple OMD config settings, these need to be converted here.
    #
    # Sadly we can not use the Transform() valuespecs, because each configvar
    # only get's the value associated with it's config key.
    def _from_omd_config(self, config):
        settings = {}

        for key, value in config.items():
            if value == "on":
                settings[key] = True
            elif value == "off":
                settings[key] = False
            else:
                settings[key] = value

        if "LIVESTATUS_TCP" in settings:
            if settings["LIVESTATUS_TCP"]:
                settings["LIVESTATUS_TCP"] = {
                    "port": int(settings["LIVESTATUS_TCP_PORT"]),
                }
                del settings["LIVESTATUS_TCP_PORT"]

                # Be compatible to older sites that don't have the key in their config yet
                settings.setdefault("LIVESTATUS_TCP_ONLY_FROM", "0.0.0.0")

                if settings["LIVESTATUS_TCP_ONLY_FROM"] != "0.0.0.0":
                    settings["LIVESTATUS_TCP"]["only_from"] = \
                        settings["LIVESTATUS_TCP_ONLY_FROM"].split()

                del settings["LIVESTATUS_TCP_ONLY_FROM"]
            else:
                settings["LIVESTATUS_TCP"] = None

        if "NSCA" in settings:
            if settings["NSCA"]:
                settings["NSCA"] = int(settings["NSCA_TCP_PORT"])
            else:
                settings["NSCA"] = None

        if "MKEVENTD" in settings:
            if settings["MKEVENTD"]:
                settings["MKEVENTD"] = []

                for proto in ["SNMPTRAP", "SYSLOG", "SYSLOG_TCP"]:
                    if settings["MKEVENTD_%s" % proto]:
                        settings["MKEVENTD"].append(proto)
            else:
                settings["MKEVENTD"] = None

        # Convert from OMD key (to lower, add "site_" prefix)
        settings = dict([("site_%s" % key.lower(), val) for key, val in settings.items()])

        return settings

    # Bring the WATO internal representation int OMD configuration settings.
    # Counterpart of the _from_omd_config() method.
    def _to_omd_config(self, config):
        settings = {}

        # Convert to OMD key
        config = dict([(key.upper()[5:], val) for key, val in config.items()])

        if "LIVESTATUS_TCP" in config:
            if config["LIVESTATUS_TCP"] is not None:
                config["LIVESTATUS_TCP_PORT"] = "%s" % config["LIVESTATUS_TCP"]["port"]

                if "only_from" in config["LIVESTATUS_TCP"]:
                    config["LIVESTATUS_TCP_ONLY_FROM"] = " ".join(
                        config["LIVESTATUS_TCP"]["only_from"])
                else:
                    config["LIVESTATUS_TCP_ONLY_FROM"] = "0.0.0.0"

                config["LIVESTATUS_TCP"] = "on"
            else:
                config["LIVESTATUS_TCP"] = "off"

        if "NSCA" in config:
            if config["NSCA"] is not None:
                config["NSCA_TCP_PORT"] = "%s" % config["NSCA"]
                config["NSCA"] = "on"
            else:
                config["NSCA"] = "off"

        if "MKEVENTD" in config:
            if config["MKEVENTD"] is not None:
                for proto in ["SNMPTRAP", "SYSLOG", "SYSLOG_TCP"]:
                    config["MKEVENTD_%s" % proto] = proto in config["MKEVENTD"]

                config["MKEVENTD"] = "on"

            else:
                config["MKEVENTD"] = "off"

        for key, value in config.items():
            if isinstance(value, bool):
                settings[key] = "on" if value else "off"
            else:
                settings[key] = "%s" % value

        return settings


#.
#   .--External API--------------------------------------------------------.
#   |      _____      _                        _      _    ____ ___        |
#   |     | ____|_  _| |_ ___ _ __ _ __   __ _| |    / \  |  _ \_ _|       |
#   |     |  _| \ \/ / __/ _ \ '__| '_ \ / _` | |   / _ \ | |_) | |        |
#   |     | |___ >  <| ||  __/ |  | | | | (_| | |  / ___ \|  __/| |        |
#   |     |_____/_/\_\\__\___|_|  |_| |_|\__,_|_| /_/   \_\_|  |___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions called by others that import wato (such as views)         |
#   '----------------------------------------------------------------------'


# Return a list with all the titles of the paths'
# components, e.g. "muc/north" -> [ "Main Directory", "Munich", "North" ]
def get_folder_title_path(path, with_links=False):
    # In order to speed this up, we work with a per HTML-request cache
    cache_name = "wato_folder_titles" + (with_links and "_linked" or "")
    cache = html.set_cache_default(cache_name, {})
    if path not in cache:
        cache[path] = Folder.folder(path).title_path(with_links)
    return cache[path]


# Return the title of a folder - which is given as a string path
def get_folder_title(path):
    folder = Folder.folder(path)
    if folder:
        return folder.title()
    return path


#.
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A host attribute is something that is inherited from folders to      |
#   | hosts. Examples are the IP address and the host tags.                |
#   '----------------------------------------------------------------------'


# TODO: Refactor declare_host_attribute() setting private attributes here
class Attribute(object):
    # The constructor stores name and title. If those are
    # dynamic then leave them out and override name() and
    # title()
    def __init__(self, name=None, title=None, help_txt=None, default_value=None):
        self._name = name
        self._title = title
        self._help = help_txt
        self._default_value = default_value

        self._show_in_table = True
        self._show_in_folder = True
        self._show_in_host_search = False
        self._show_in_form = True
        self._show_inherited_value = True
        self._depends_on_tags = []
        self._depends_on_roles = []
        self._editable = True
        self._from_config = False

    # Return the name (= identifier) of the attribute
    def name(self):
        return self._name

    # Return the name of the Nagios configuration variable
    # if this is a Nagios-bound attribute (e.g. "alias" or "_SERIAL")
    def nagios_name(self):
        return None

    # Return the title to be displayed to the user
    def title(self):
        return self._title

    # Return an optional help text
    def help(self):
        return self._help

    # Return the default value for new hosts
    def default_value(self):
        return self._default_value

    # Render HTML code displaying a value
    def paint(self, value, hostname):
        return "", value

    # Whether or not the user is able to edit this attribute. If
    # not, the value is shown read-only (when the user is permitted
    # to see the attribute).
    def may_edit(self):
        return True

    # Whether or not to show this attribute in tables.
    # This value is set by declare_host_attribute
    def show_in_table(self):
        return self._show_in_table

    # Whether or not to show this attribute in the edit form.
    # This value is set by declare_host_attribute
    def show_in_form(self):
        return self._show_in_form

    # Whether or not to make this attribute configurable in
    # files and folders (as defaule value for the hosts)
    def show_in_folder(self):
        return self._show_in_folder

    # Whether or not to make this attribute configurable in
    # the host search form
    def show_in_host_search(self):
        return self._show_in_host_search

    # Whether or not this attribute can be edited after creation
    # of the object
    def editable(self):
        return self._editable

    # Whether it is allowed that a host has no explicit
    # value here (inherited or direct value). An mandatory
    # has *no* default value.
    def is_mandatory(self):
        return False

    # Return information about the user roles we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_roles is set by declare_host_attribute().
    def depends_on_roles(self):
        return self._depends_on_roles

    # Return information about whether or not either the
    # inherited value or the default value should be shown
    # for an attribute.
    # _depends_on_roles is set by declare_host_attribute().
    def show_inherited_value(self):
        return self._show_inherited_value

    # Return information about the host tags we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_tags is set by declare_host_attribute().
    def depends_on_tags(self):
        return self._depends_on_tags

    # Whether or not this attribute has been created from the
    # config of the site.
    # The method is usually not overridden, but the variable
    # _from_config is set by declare_host_attribute().
    def from_config(self):
        return self._from_config

    # Render HTML input fields displaying the value and
    # make it editable. If filter == True, then the field
    # is to be displayed in filter mode (as part of the
    # search filter)
    def render_input(self, varprefix, value):
        pass

    # Create value from HTML variables.
    def from_html_vars(self, varprefix):
        return None

    # Check whether this attribute needs to be validated at all
    # Attributes might be permanently hidden (show_in_form = False)
    # or dynamically hidden by the depends_on_tags, editable features
    def needs_validation(self, for_what):
        if not self.is_visible(for_what):
            return False
        return html.request.var('attr_display_%s' % self._name, "1") == "1"

    # Gets the type of current view as argument and returns whether or not
    # this attribute is shown in this type of view
    def is_visible(self, for_what):
        if for_what in ["host", "cluster", "bulk"] and not self.show_in_form():
            return False
        elif for_what == "folder" and not self.show_in_folder():
            return False
        elif for_what == "host_search" and not self.show_in_host_search():
            return False
        return True

    # Check if the value entered by the user is valid.
    # This method may raise MKUserError in case of invalid user input.
    def validate_input(self, value, varprefix):
        pass

    # If this attribute should be present in Nagios as
    # a host custom macro, then the value of that macro
    # should be returned here - otherwise None
    def to_nagios(self, value):
        return None

    # Checks if the give value matches the search attributes
    # that are represented by the current HTML variables.
    def filter_matches(self, crit, value, hostname):
        return crit == value

    # Host tags to set for this host
    def get_tag_list(self, value):
        return []

    @property
    def is_checkbox_tag(self):
        return False

    @property
    def is_tag_attribute(self):
        return False


# A simple text attribute. It is stored in
# a Python unicode string
class TextAttribute(Attribute):
    def __init__(self,
                 name,
                 title,
                 help_txt=None,
                 default_value="",
                 mandatory=False,
                 allow_empty=True,
                 size=25):
        Attribute.__init__(self, name, title, help_txt, default_value)
        self._mandatory = mandatory
        self._allow_empty = allow_empty
        self._size = size

    def paint(self, value, hostname):
        if not value:
            return "", ""
        return "", value

    def is_mandatory(self):
        return self._mandatory

    def render_input(self, varprefix, value):
        if value is None:
            value = ""
        html.text_input(varprefix + "attr_" + self.name(), value, size=self._size)

    def from_html_vars(self, varprefix):
        value = html.get_unicode_input(varprefix + "attr_" + self.name())
        if value is None:
            value = ""
        return value.strip()

    def validate_input(self, value, varprefix):
        if self._mandatory and not value:
            raise MKUserError(varprefix + "attr_" + self.name(),
                              _("Please specify a value for %s") % self.title())
        if not self._allow_empty and value.strip() == "":
            raise MKUserError(
                varprefix + "attr_" + self.name(),
                _("%s may be missing, if must not be empty if it is set.") % self.title())

    def filter_matches(self, crit, value, hostname):
        if value is None:  # Host does not have this attribute
            value = ""

        return host_attribute_matches(crit, value)


# An attribute using the generic ValueSpec mechanism
class ValueSpecAttribute(Attribute):
    def __init__(self, name, vs):
        Attribute.__init__(self, name)
        self._valuespec = vs

    def valuespec(self):
        return self._valuespec

    def title(self):
        return self._valuespec.title()

    def help(self):
        return self._valuespec.help()

    def default_value(self):
        return self._valuespec.default_value()

    def paint(self, value, hostname):
        return "", \
            self._valuespec.value_to_text(value)

    def render_input(self, varprefix, value):
        self._valuespec.render_input(varprefix + self._name, value)

    def from_html_vars(self, varprefix):
        return self._valuespec.from_html_vars(varprefix + self._name)

    def validate_input(self, value, varprefix):
        self._valuespec.validate_value(value, varprefix + self._name)


# A simple text attribute that is not editable by the user.
# It can be used to store context information from other
# systems (e.g. during an import of a host database from
# another system).
class FixedTextAttribute(TextAttribute):
    def __init__(self, name, title, help_txt=None):
        TextAttribute.__init__(self, name, title, help_txt, None)
        self._mandatory = False

    def render_input(self, varprefix, value):
        if value is not None:
            html.hidden_field(varprefix + "attr_" + self.name(), value)
            html.write(value)

    def from_html_vars(self, varprefix):
        return html.request.var(varprefix + "attr_" + self.name())


# A text attribute that is stored in a Nagios custom macro
class NagiosTextAttribute(TextAttribute):
    def __init__(self,
                 name,
                 nag_name,
                 title,
                 help_txt=None,
                 default_value="",
                 mandatory=False,
                 allow_empty=True,
                 size=25):
        TextAttribute.__init__(self, name, title, help_txt, default_value, mandatory, allow_empty,
                               size)
        self.nag_name = nag_name

    def nagios_name(self):
        return self.nag_name

    def to_nagios(self, value):
        if value:
            return value
        return None


# An attribute for selecting one item out of list using
# a drop down box (<select>). Enumlist is a list of
# pairs of keyword / title. The type of value is string.
# In all cases where no value is defined or the value is
# not in the enumlist, the default value is being used.
class EnumAttribute(Attribute):
    def __init__(self, name, title, help_txt, default_value, enumlist):
        Attribute.__init__(self, name, title, help_txt, default_value)
        self._enumlist = enumlist
        self._enumdict = dict(enumlist)

    def paint(self, value, hostname):
        return "", self._enumdict.get(value, self.default_value())

    def render_input(self, varprefix, value):
        html.dropdown(varprefix + "attr_" + self.name(), self._enumlist, value)

    def from_html_vars(self, varprefix):
        return html.request.var(varprefix + "attr_" + self.name(), self.default_value())


class HostTagAttribute(ValueSpecAttribute):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def is_checkbox_tag(self):
        # type: () -> bool
        raise NotImplementedError()

    def __init__(self, valuespec, tag_id, tag_list):
        self._taglist = tag_list
        super(HostTagAttribute, self).__init__(name="tag_" + tag_id, vs=valuespec)

    @property
    def is_tag_attribute(self):
        return True

    def _get_tag_choices(self, tag_list):
        return [(e[0], _u(e[1])) for e in tag_list]

    # TODO: Can we move this to some other place?
    def get_tag_value(self, tags):
        """Special function for computing the setting of a specific
        tag group from the total list of tags of a host"""
        for entry in self._taglist:
            if entry[0] in tags:
                return entry[0]
        return None

    # TODO: Can we move this to some other place?
    def get_tag_list(self, value):
        """Return list of host tags to set (handles secondary tags)"""
        for entry in self._taglist:
            if entry[0] == value:
                if len(entry) >= 3:
                    taglist = [value] + entry[2]
                else:
                    taglist = [value]
                if taglist[0] is None:
                    taglist = taglist[1:]
                return taglist
        return []  # No matching tag


class HostTagListAttribute(HostTagAttribute):
    """A selection dropdown for a host tag"""

    def __init__(self, tag_id, title, tag_list):
        vs = DropdownChoice(
            title=title,
            choices=self._get_tag_choices(tag_list),
            default_value=tag_list[0][0],
            on_change="cmk.wato.fix_visibility();",
            encode_value=False,
        )
        super(HostTagListAttribute, self).__init__(vs, tag_id, tag_list)

    @property
    def is_checkbox_tag(self):
        return False

    @property
    def is_tag_attribute(self):
        return True


class HostTagCheckboxAttribute(HostTagAttribute):
    """A checkbox for a host tag group"""

    def __init__(self, tag_id, title, tag_list):
        vs = Checkbox(
            title=title,
            label=_u(tag_list[0][1]),
            true_label=title,
            false_label="%s %s" % (_("Not"), title),
            onclick="cmk.wato.fix_visibility();",
        )
        super(HostTagCheckboxAttribute, self).__init__(vs, tag_id, tag_list)

    @property
    def is_checkbox_tag(self):
        return True

    def render_input(self, varprefix, value):
        super(HostTagCheckboxAttribute, self).render_input(varprefix, bool(value))

    def from_html_vars(self, varprefix):
        if super(HostTagCheckboxAttribute, self).from_html_vars(varprefix):
            return self._taglist[0][0]
        return None


class NagiosValueSpecAttribute(ValueSpecAttribute):
    def __init__(self, name, nag_name, vs):
        ValueSpecAttribute.__init__(self, name, vs)
        self.nag_name = nag_name

    def nagios_name(self):
        return self.nag_name

    def to_nagios(self, value):
        value = self._valuespec.value_to_text(value)
        if value:
            return value
        return None


# Attribute needed for folder permissions
class ContactGroupsAttribute(Attribute):
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self):
        url = "wato.py?mode=rulesets&group=grouping"
        Attribute.__init__(
            self, "contactgroups", _("Permissions"),
            _("Only members of the contact groups listed here have WATO permission "
              "to the host / folder. If you want, you can make those contact groups "
              "automatically also <b>monitoring contacts</b>. This is completely "
              "optional. Assignment of host and services to contact groups "
              "can be done by <a href='%s'>rules</a> as well.") % url)
        self._default_value = (True, [])
        self._contactgroups = None
        self._users = None
        self._loaded_at = None

    def paint(self, value, hostname):
        value = convert_cgroups_from_tuple(value)
        texts = []
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp=lambda a, b: cmp(a[1]['alias'], b[1]['alias']))
        for name, cgroup in items:
            if name in value["groups"]:
                display_name = cgroup.get("alias", name)
                texts.append('<a href="wato.py?mode=edit_contact_group&edit=%s">%s</a>' %
                             (name, display_name))
        result = ", ".join(texts)
        if texts and value["use"]:
            result += html.render_span(
                html.render_b("*"),
                title=_("These contact groups are also used in the monitoring configuration."))
        return "", result

    def render_input(self, varprefix, value):
        value = convert_cgroups_from_tuple(value)

        # If we're just editing a host, then some of the checkboxes will be missing.
        # This condition is not very clean, but there is no other way to savely determine
        # the context.
        is_host = bool(html.request.var("host")) or html.request.var("mode") == "newhost"
        is_search = varprefix == "host_search"

        # Only show contact groups I'm currently in and contact
        # groups already listed here.
        self.load_data()
        self._vs_contactgroups().render_input(varprefix + self._name, value['groups'])

        html.hr()

        if is_host:
            html.checkbox(
                varprefix + self._name + "_use",
                value["use"],
                label=_("Add these contact groups to the host"))

        elif not is_search:
            html.checkbox(
                varprefix + self._name + "_recurse_perms",
                value["recurse_perms"],
                label=_("Give these groups also <b>permission on all subfolders</b>"))
            html.hr()
            html.checkbox(
                varprefix + self._name + "_use",
                value["use"],
                label=_("Add these groups as <b>contacts</b> to all hosts in this folder"))
            html.br()
            html.checkbox(
                varprefix + self._name + "_recurse_use",
                value["recurse_use"],
                label=_("Add these groups as <b>contacts in all subfolders</b>"))

        html.hr()
        html.help(
            _("With this option contact groups that are added to hosts are always "
              "being added to services, as well. This only makes a difference if you have "
              "assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. "
              "As long as you do not have any such rule a service always inherits all contact groups "
              "from its host."))
        html.checkbox(
            varprefix + self._name + "_use_for_services",
            value.get("use_for_services", False),
            label=_("Always add host contact groups also to its services"))

    def load_data(self):
        # Make cache valid only during this HTTP request
        if self._loaded_at == id(html):
            return
        self._loaded_at = id(html)
        self._contactgroups = userdb.load_group_information().get("contact", {})

    def from_html_vars(self, varprefix):
        self.load_data()

        cgs = self._vs_contactgroups().from_html_vars(varprefix + self._name)

        return {
            "groups": cgs,
            "recurse_perms": html.get_checkbox(varprefix + self._name + "_recurse_perms"),
            "use": html.get_checkbox(varprefix + self._name + "_use"),
            "use_for_services": html.get_checkbox(varprefix + self._name + "_use_for_services"),
            "recurse_use": html.get_checkbox(varprefix + self._name + "_recurse_use"),
        }

    def filter_matches(self, crit, value, hostname):
        value = convert_cgroups_from_tuple(value)
        # Just use the contact groups for searching
        for contact_group in crit["groups"]:
            if contact_group not in value["groups"]:
                return False
        return True

    def _vs_contactgroups(self):
        cg_choices = sorted([(cg_id, cg_attrs.get("alias", cg_id))
                             for cg_id, cg_attrs in self._contactgroups.items()],
                            key=lambda x: x[1])
        return DualListChoice(choices=cg_choices, rows=20, size=100)


def update_config_based_host_attributes():
    _clear_config_based_host_attributes()
    declare_host_tag_attributes()
    declare_custom_host_attrs()

    Folder.invalidate_caches()


def _clear_config_based_host_attributes():
    for name, attr in cmk.gui.watolib.host_attributes.attributes().items():
        if attr.from_config():
            undeclare_host_attribute(name)


def declare_host_tag_attributes():
    for topic, grouped_tags in group_hosttags_by_topic(config.host_tag_groups()):
        for entry in grouped_tags:
            # if the entry has o fourth component, then its
            # the tag dependency defintion.
            depends_on_tags = []
            depends_on_roles = []
            attr_editable = True
            if len(entry) >= 6:
                attr_editable = entry[5]
            if len(entry) >= 5:
                depends_on_roles = entry[4]
            if len(entry) >= 4:
                depends_on_tags = entry[3]

            if not topic:
                topic = _('Host tags')

            if len(entry[2]) == 1:
                vs = HostTagCheckboxAttribute(*entry[:3])
            else:
                vs = HostTagListAttribute(*entry[:3])

            cmk.gui.watolib.host_attributes.declare_host_attribute(
                vs,
                show_in_table=False,
                show_in_folder=True,
                editable=attr_editable,
                depends_on_tags=depends_on_tags,
                depends_on_roles=depends_on_roles,
                topic=topic,
                from_config=True,
            )


def declare_custom_host_attrs():
    for attr in config.wato_host_attrs:
        vs = globals()[attr['type']](title=attr['title'], help=attr['help'])

        if attr['add_custom_macro']:
            a = NagiosValueSpecAttribute(attr["name"], "_" + attr["name"], vs)
        else:
            a = ValueSpecAttribute(attr["name"], vs)

        cmk.gui.watolib.host_attributes.declare_host_attribute(
            a,
            show_in_table=attr['show_in_table'],
            topic=attr['topic'],
            from_config=True,
        )


def get_sorted_host_attribute_topics(for_what):
    # show attributes grouped by topics, in order of their
    # appearance. If only one topic exists, do not show topics
    # Make sure, that the topics "Basic settings" and host tags
    # are always show first.
    # TODO: Clean this up! Implement some explicit sorting
    topics = [None]
    if config.host_tag_groups():
        topics.append(_("Address"))
        topics.append(_("Data sources"))
        topics.append(_("Host tags"))

    # The remaining topics are shown in the order of the
    # appearance of the attribute declarations:
    for attr, topic in all_host_attributes():
        if topic not in topics and attr.is_visible(for_what):
            topics.append(topic)

    return [(t, _("Basic settings") if t is None else _u(t)) for t in topics]


def get_sorted_host_attributes_by_topic(topic):
    # Hack to sort the address family host tag attribute above the IPv4/v6 addresses
    # TODO: Clean this up by implementing some sort of explicit sorting
    def sort_host_attributes(a, b):
        if a[0].name() == "tag_address_family":
            return -1
        return 0

    attributes = []
    for attr, atopic in sorted(all_host_attributes(), cmp=sort_host_attributes):
        if atopic == topic:
            attributes.append(attr)
    return attributes


def save_global_settings(vars_, site_specific=False):
    per_domain = {}
    # TODO: Uee _get_global_config_var_names() from domain class?
    for config_variable_class in config_variable_registry.values():
        config_variable = config_variable_class()
        domain = config_variable.domain()
        varname = config_variable.ident()
        if varname not in vars_:
            continue
        per_domain.setdefault(domain.ident, {})[varname] = vars_[varname]

    # The global setting wato_enabled is not registered in the configuration domains
    # since the user must not change it directly. It is set by D-WATO on slave sites.
    if "wato_enabled" in vars_:
        per_domain.setdefault(ConfigDomainGUI.ident, {})["wato_enabled"] = vars_["wato_enabled"]
    if "userdb_automatic_sync" in vars_:
        per_domain.setdefault(ConfigDomainGUI.ident,
                              {})["userdb_automatic_sync"] = vars_["userdb_automatic_sync"]

    for domain in ConfigDomain.enabled_domains():
        if site_specific:
            domain().save_site_globals(per_domain.get(domain.ident, {}))
        else:
            domain().save(per_domain.get(domain.ident, {}))


def save_site_global_settings(vars_):
    save_global_settings(vars_, site_specific=True)


def get_login_secret(create_on_demand=False):
    path = cmk.utils.paths.var_dir + "/wato/automation_secret.mk"

    secret = store.load_data_from_file(path)
    if secret is not None:
        return secret

    if not create_on_demand:
        return None

    secret = cmk.gui.utils.get_random_string(32)
    store.save_data_to_file(path, secret)
    return secret


# Returns the ID of our site. This function only works in replication
# mode and looks for an entry connecting to the local socket.
def our_site_id():
    for site_id in config.allsites():
        if config.site_is_local(site_id):
            return site_id
    return None


def do_site_login(site_id, name, password):
    sites = SiteManagementFactory().factory().load_sites()
    site = sites[site_id]
    if not name:
        raise MKUserError("_name", _("Please specify your administrator login on the remote site."))
    if not password:
        raise MKUserError("_passwd", _("Please specify your password."))

    # Trying basic auth AND form based auth to ensure the site login works.
    # Adding _ajaxid makes the web service fail silently with an HTTP code and
    # not output HTML code for an error screen.
    url = site["multisiteurl"] + 'login.py'
    post_data = {
        '_login': '1',
        '_username': name,
        '_password': password,
        '_origtarget': 'automation_login.py?_version=%s&_edition_short=%s' % (cmk.__version__,
                                                                              cmk.edition_short()),
        '_plain_error': '1',
    }
    response = get_url(
        url, site.get('insecure', False), auth=(name, password), data=post_data).strip()
    if '<html>' in response.lower():
        message = _("Authentication to web service failed.<br>Message:<br>%s") % \
            html.strip_tags(html.strip_scripts(response))
        if config.debug:
            message += "<br>" + _("Automation URL:") + " <tt>%s</tt><br>" % url
        raise MKAutomationException(message)
    elif not response:
        raise MKAutomationException(_("Empty response from web service"))
    else:
        try:
            return ast.literal_eval(response)
        except:
            raise MKAutomationException(response)


# Returns a list of site ids which gets the Event Console configuration replicated
def get_event_console_sync_sites():
    return [s[0] for s in config.get_event_console_site_choices()]


def get_notification_sync_sites():
    return sorted(site_id for site_id, _site in config.wato_slave_sites()
                  if not config.site_is_local(site_id))


# TODO: cleanup all call sites to this name
is_wato_slave_site = config.is_wato_slave_site
site_choices = config.site_choices

PushSnapshotRequest = NamedTuple("PushSnapshotRequest", [("site_id", str), ("tar_content", str)])


@automation_command_registry.register
class AutomationPushSnapshot(AutomationCommand):
    def command_name(self):
        return "push-snapshot"

    def get_request(self):
        # type: () -> PushSnapshotRequest
        site_id = html.request.var("siteid")
        self._verify_slave_site_config(site_id)

        snapshot = html.request.uploaded_file("snapshot")
        if not snapshot:
            raise MKGeneralException(_('Invalid call: The snapshot is missing.'))

        return PushSnapshotRequest(site_id=site_id, tar_content=snapshot[2])

    def execute(self, request):
        # type: (PushSnapshotRequest) -> bool
        multitar.extract_from_buffer(request.tar_content,
                                     cmk.gui.watolib.changes.get_replication_paths())

        try:
            self._save_site_globals_on_slave_site(request.tar_content)

            confirm_all_local_changes()  # pending changes are lost

            hooks.call("snapshot-pushed")

            # Create rule making this site only monitor our hosts
            create_distributed_wato_file(request.site_id, is_slave=True)
        except Exception:
            raise MKGeneralException(
                _("Failed to deploy configuration: \"%s\". "
                  "Please note that the site configuration has been synchronized "
                  "partially.") % traceback.format_exc())

        log_audit(None, "replication",
                  _("Synchronized with master (my site id is %s.)") % request.site_id)

        return True

    def _save_site_globals_on_slave_site(self, tarcontent):
        tmp_dir = cmk.utils.paths.tmp_dir + "/sitespecific-%s" % id(html)
        try:
            if not os.path.exists(tmp_dir):
                store.mkdir(tmp_dir)

            multitar.extract_from_buffer(tarcontent, [("dir", "sitespecific", tmp_dir)])

            site_globals = store.load_data_from_file(tmp_dir + "/sitespecific.mk", {})
            save_site_global_settings(site_globals)
        finally:
            shutil.rmtree(tmp_dir)


def push_user_profiles_to_site_transitional_wrapper(site, user_profiles):
    try:
        return push_user_profiles_to_site(site, user_profiles)
    except MKAutomationException as e:
        if "Invalid automation command: push-profiles" in "%s" % e:
            failed_info = []
            for user_id, user in user_profiles.iteritems():
                result = legacy_push_user_profile_to_site(site, user_id, user)
                if result != True:
                    failed_info.append(result)

            if failed_info:
                return "\n".join(failed_info)
            return True
        else:
            raise


def legacy_push_user_profile_to_site(site, user_id, profile):
    url = site["multisiteurl"] + "automation.py?" + html.urlencode_vars([
        ("command", "push-profile"),
        ("secret", site["secret"]),
        ("siteid", site['id']),
        ("debug", config.debug and "1" or ""),
    ])

    response = get_url(
        url,
        site.get('insecure', False),
        data={
            'user_id': user_id,
            'profile': mk_repr(profile),
        },
        timeout=60)

    if not response:
        raise MKAutomationException(_("Empty output from remote site."))

    try:
        response = mk_eval(response)
    except:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException("%s: <pre>%s</pre>" % (_("Got invalid data"), response))
    return response


def push_user_profiles_to_site(site, user_profiles):
    return do_remote_automation(
        site, "push-profiles", [("profiles", repr(user_profiles))], timeout=60)


PushUserProfilesRequest = NamedTuple("PushUserProfilesRequest", [("user_profiles", dict)])


@automation_command_registry.register
class PushUserProfilesToSite(AutomationCommand):
    def command_name(self):
        return "push-profiles"

    def get_request(self):
        return PushUserProfilesRequest(ast.literal_eval(html.request.var("profiles")))

    def execute(self, request):
        user_profiles = request.user_profiles

        if not user_profiles:
            raise MKGeneralException(_('Invalid call: No profiles set.'))

        users = userdb.load_users(lock=True)
        for user_id, profile in user_profiles.iteritems():
            users[user_id] = profile
        userdb.save_users(users)
        return True


# Add pending entry to make sync possible later for admins
def add_profile_replication_change(site_id, result):
    add_change(
        "edit-users",
        _('Profile changed (sync failed: %s)') % result,
        sites=[site_id],
        need_restart=False)


#.
#   .--Hooks---------------------------------------------------------------.
#   |                     _   _             _                              |
#   |                    | | | | ___   ___ | | _____                       |
#   |                    | |_| |/ _ \ / _ \| |/ / __|                      |
#   |                    |  _  | (_) | (_) |   <\__ \                      |
#   |                    |_| |_|\___/ \___/|_|\_\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Hooks allow to register functions that are being called on certain   |
#   | operations. You can e.g. get called whenever changes are activated.  |
#   '----------------------------------------------------------------------'

#.
#   .--Host Tag Conditions-------------------------------------------------.
#   |                _   _           _     _____                           |
#   |               | | | | ___  ___| |_  |_   _|_ _  __ _                 |
#   |               | |_| |/ _ \/ __| __|   | |/ _` |/ _` |                |
#   |               |  _  | (_) \__ \ |_    | | (_| | (_| |                |
#   |               |_| |_|\___/|___/\__|   |_|\__,_|\__, |                |
#   |                                                |___/                 |
#   |            ____                _ _ _   _                             |
#   |           / ___|___  _ __   __| (_) |_(_) ___  _ __  ___             |
#   |          | |   / _ \| '_ \ / _` | | __| |/ _ \| '_ \/ __|            |
#   |          | |__| (_) | | | | (_| | | |_| | (_) | | | \__ \            |
#   |           \____\___/|_| |_|\__,_|_|\__|_|\___/|_| |_|___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


# ValueSpec for editing a tag-condition
class HostTagCondition(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)

    def render_input(self, varprefix, value):
        render_condition_editor(value, varprefix)

    def from_html_vars(self, varprefix):
        return get_tag_conditions(varprefix=varprefix)

    def canonical_value(self):
        return []

    def value_to_text(self, value):
        return "|".join(value)

    def validate_datatype(self, value, varprefix):
        if not isinstance(value, list):
            raise MKUserError(varprefix,
                              _("The list of host tags must be a list, but "
                                "is %r") % type(value))
        for x in value:
            if not isinstance(x, str):
                raise MKUserError(
                    varprefix,
                    _("The list of host tags must only contain strings "
                      "but also contains %r") % x)

    def validate_value(self, value, varprefix):
        pass


# Render HTML input fields for editing a tag based condition
def render_condition_editor(tag_specs, varprefix=""):
    if varprefix:
        varprefix += "_"

    if not config.aux_tags() + config.host_tag_groups():
        html.write(
            _("You have not configured any <a href=\"wato.py?mode=hosttags\">host tags</a>."))
        return

    # Determine current (default) setting of tag by looking
    # into tag_specs (e.g. [ "snmp", "!tcp", "test" ] )
    def current_tag_setting(choices):
        default_tag = None
        ignore = True
        for t in tag_specs:
            if t[0] == '!':
                n = True
                t = t[1:]
            else:
                n = False
            if t in [x[0] for x in choices]:
                default_tag = t
                ignore = False
                negate = n
        if ignore:
            deflt = "ignore"
        elif negate:
            deflt = "isnot"
        else:
            deflt = "is"
        return default_tag, deflt

    # Show dropdown with "is/isnot/ignore" and beginning
    # of div that is switched visible by is/isnot
    def tag_condition_dropdown(tagtype, deflt, id_):
        html.open_td()
        dropdown_id = varprefix + tagtype + "_" + id_
        onchange = "cmk.valuespecs.toggle_tag_dropdown(this, '%stag_sel_%s');" % (varprefix, id_)
        choices = [
            ("ignore", _("ignore")),
            ("is", _("is")),
            ("isnot", _("isnot")),
        ]
        html.dropdown(dropdown_id, choices, deflt=deflt, onchange=onchange)
        html.close_td()

        html.open_td(class_="tag_sel")
        if html.form_submitted():
            div_is_open = html.request.var(dropdown_id, "ignore") != "ignore"
        else:
            div_is_open = deflt != "ignore"
        html.open_div(
            id_="%stag_sel_%s" % (varprefix, id_),
            style="display: none;" if not div_is_open else None)

    auxtags = group_hosttags_by_topic(config.aux_tags())
    hosttags = group_hosttags_by_topic(config.host_tag_groups())
    all_topics = set([])
    for topic, _taggroups in auxtags + hosttags:
        all_topics.add(topic)
    all_topics = list(all_topics)
    all_topics.sort()
    make_foldable = len(all_topics) > 1
    for topic in all_topics:
        if make_foldable:
            html.begin_foldable_container("topic", varprefix + topic, True,
                                          HTML("<b>%s</b>" % (_u(topic))))
        html.open_table(class_=["hosttags"])

        # Show main tags
        for t, grouped_tags in hosttags:
            if t == topic:
                for entry in grouped_tags:
                    id_, title, choices = entry[:3]
                    html.open_tr()
                    html.open_td(class_="title")
                    html.write("%s: &nbsp;" % _u(title))
                    html.close_td()
                    default_tag, deflt = current_tag_setting(choices)
                    tag_condition_dropdown("tag", deflt, id_)
                    if len(choices) == 1:
                        html.write_text(" " + _("set"))
                    else:
                        html.dropdown(
                            varprefix + "tagvalue_" + id_,
                            [(t[0], _u(t[1])) for t in choices if t[0] is not None],
                            deflt=default_tag)
                    html.close_div()
                    html.close_td()
                    html.close_tr()

        # And auxiliary tags
        for t, grouped_tags in auxtags:
            if t == topic:
                for id_, title in grouped_tags:
                    html.open_tr()
                    html.open_td(class_="title")
                    html.write("%s: &nbsp;" % _u(title))
                    html.close_td()
                    default_tag, deflt = current_tag_setting([(id_, _u(title))])
                    tag_condition_dropdown("auxtag", deflt, id_)
                    html.write_text(" " + _("set"))
                    html.close_div()
                    html.close_td()
                    html.close_tr()

        html.close_table()
        if make_foldable:
            html.end_foldable_container()


# Retrieve current tag condition settings from HTML variables
def get_tag_conditions(varprefix=""):
    if varprefix:
        varprefix += "_"
    # Main tags
    tag_list = []
    for entry in config.host_tag_groups():
        id_, _title, tags = entry[:3]
        mode = html.request.var(varprefix + "tag_" + id_)
        if len(tags) == 1:
            tagvalue = tags[0][0]
        else:
            tagvalue = html.request.var(varprefix + "tagvalue_" + id_)

        if mode == "is":
            tag_list.append(tagvalue)
        elif mode == "isnot":
            tag_list.append("!" + tagvalue)

    # Auxiliary tags
    for id_, _title in config.aux_tags():
        mode = html.request.var(varprefix + "auxtag_" + id_)
        if mode == "is":
            tag_list.append(id_)
        elif mode == "isnot":
            tag_list.append("!" + id_)

    return tag_list


#.
#   .--Handler scripts-----------------------------------------------------.
#   |                 _   _                 _ _                            |
#   |                | | | | __ _ _ __   __| | | ___ _ __                  |
#   |                | |_| |/ _` | '_ \ / _` | |/ _ \ '__|                 |
#   |                |  _  | (_| | | | | (_| | |  __/ |                    |
#   |                |_| |_|\__,_|_| |_|\__,_|_|\___|_|                    |
#   |                                                                      |
#   |                                  _       _                           |
#   |                    ___  ___ _ __(_)_ __ | |_ ___                     |
#   |                   / __|/ __| '__| | '_ \| __/ __|                    |
#   |                   \__ \ (__| |  | | |_) | |_\__ \                    |
#   |                   |___/\___|_|  |_| .__/ \__|___/                    |
#   |                                   |_|                                |
#   +----------------------------------------------------------------------+
#   | Common code for reading and offering notification scripts and alert  |
#   | handlers.                                                            |
#   '----------------------------------------------------------------------'

# Example header of a notification script:
#!/usr/bin/python
# HTML Emails with included graphs
# Bulk: yes
# Argument 1: Full system path to the pnp4nagios index.php for fetching the graphs. Usually auto configured in OMD.
# Argument 2: HTTP-URL-Prefix to open Multisite. When provided, several links are added to the mail.
#
# This script creates a nifty HTML email in multipart format with
# attached graphs and such neat stuff. Sweet!


def load_user_scripts_from(adir):
    scripts = {}
    if os.path.exists(adir):
        for entry in os.listdir(adir):
            entry = entry.decode("utf-8")
            path = adir + "/" + entry
            if os.path.isfile(path) and os.access(path, os.X_OK):
                info = {"title": entry, "bulk": False}
                try:
                    lines = file(path)
                    lines.next()
                    line = lines.next().decode("utf-8").strip()
                    if line.startswith("#") and "encoding:" in line:
                        line = lines.next().strip()
                    if line.startswith("#"):
                        info["title"] = line.lstrip("#").strip().split("#", 1)[0]
                    while True:
                        line = lines.next().strip()
                        if not line.startswith("#") or ":" not in line:
                            break
                        key, value = line[1:].strip().split(":", 1)
                        value = value.strip()
                        if key.lower() == "bulk":
                            info["bulk"] = (value == "yes")

                except:
                    pass
                scripts[entry] = info
    return scripts


def load_user_scripts(what):
    scripts = {}
    not_dir = cmk.utils.paths.share_dir + "/" + what
    try:
        if what == "notifications":
            # Support for setup.sh
            not_dir = cmk.utils.paths.notifications_dir
    except:
        pass

    scripts = load_user_scripts_from(not_dir)
    try:
        local_dir = cmk.utils.paths.omd_root + "/local/share/check_mk/" + what
        scripts.update(load_user_scripts_from(local_dir))
    except:
        pass

    return scripts


def load_notification_scripts():
    return load_user_scripts("notifications")


def user_script_choices(what):
    scripts = load_user_scripts(what)
    choices = [(name, info["title"]) for (name, info) in scripts.items()]
    choices.sort(cmp=lambda a, b: cmp(a[1], b[1]))
    choices = [(k, _u(v)) for k, v in choices]
    return choices


def user_script_title(what, name):
    return dict(user_script_choices(what)).get(name, name)


class RuleComment(TextAreaUnicode):
    def __init__(self, **kwargs):
        kwargs.setdefault("title", _("Comment"))
        kwargs.setdefault("help", _("An optional comment that explains the purpose of this rule."))
        kwargs.setdefault("rows", 4)
        kwargs.setdefault("cols", 80)
        super(RuleComment, self).__init__(**kwargs)

    def render_input(self, varprefix, value):
        html.open_div(style="white-space: nowrap;")

        super(RuleComment, self).render_input(varprefix, value)

        date_and_user = "%s %s: " % (time.strftime("%F", time.localtime()), config.user.id)

        html.nbsp()
        html.icon_button(
            None,
            title=_("Prefix date and your name to the comment"),
            icon="insertdate",
            onclick="cmk.valuespecs.rule_comment_prefix_date_and_user(this, '%s');" % date_and_user)
        html.close_div()


#.
#   .--Users---------------------------------------------------------------.
#   |                       _   _                                          |
#   |                      | | | |___  ___ _ __ ___                        |
#   |                      | | | / __|/ _ \ '__/ __|                       |
#   |                      | |_| \__ \  __/ |  \__ \                       |
#   |                       \___/|___/\___|_|  |___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Registers notification parameters for a certain notification script,
# e.g. "mail" or "sms". This will create:
# - A WATO host rule
# - A parametrization of the not-script also in the RBN module
# Notification parameters are always expected to be of type Dictionary.
# The match type will be set to "dict".


def register_user_script_parameters(ruleset_dict, ruleset_dict_name, ruleset_group, scriptname,
                                    valuespec):
    script_title = notification_script_title(scriptname)
    title = _("Parameters for %s") % script_title
    valuespec._title = _("Call with the following parameters:")

    register_rule(
        ruleset_group,
        ruleset_dict_name + ":" + scriptname,
        valuespec,
        title,
        itemtype=None,
        match="dict")
    ruleset_dict[scriptname] = valuespec


g_notification_parameters = {}


def register_notification_parameters(scriptname, valuespec):
    rulespec_group_class = rulespec_group_registry["monconf/notifications"]
    register_user_script_parameters(g_notification_parameters, "notification_parameters",
                                    rulespec_group_class, scriptname, valuespec)


def verify_password_policy(password):
    min_len = config.password_policy.get('min_length')
    if min_len and len(password) < min_len:
        raise MKUserError(
            'password',
            _('The given password is too short. It must have at least %d characters.') % min_len)

    num_groups = config.password_policy.get('num_groups')
    if num_groups:
        groups = {}
        for c in password:
            if c in "abcdefghijklmnopqrstuvwxyz":
                groups['lcase'] = 1
            elif c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                groups['ucase'] = 1
            elif c in "0123456789":
                groups['numbers'] = 1
            else:
                groups['special'] = 1

        if sum(groups.values()) < num_groups:
            raise MKUserError(
                'password',
                _('The password does not use enough character groups. You need to '
                  'set a password which uses at least %d of them.') % num_groups)


def notification_script_choices():
    choices = []
    for choice in user_script_choices("notifications") + [(None, _("ASCII Email (legacy)"))]:
        notificaton_plugin_name, _notification_plugin_title = choice
        if config.user.may("notification_plugin.%s" % notificaton_plugin_name):
            choices.append(choice)
    return choices


def notification_script_choices_with_parameters():
    choices = []
    for script_name, title in notification_script_choices():
        if script_name in g_notification_parameters:
            vs = g_notification_parameters[script_name]
        else:
            vs = ListOfStrings(
                title=_("Call with the following parameters:"),
                help=
                _("The given parameters are available in scripts as NOTIFY_PARAMETER_1, NOTIFY_PARAMETER_2, etc."
                 ),
                valuespec=TextUnicode(size=24),
                orientation="horizontal",
            )

        vs_alternative = Alternative(
            style="dropdown",
            elements=[
                vs,
                FixedValue(
                    None,
                    totext=_("previous notifications of this type are cancelled"),
                    title=_("Cancel previous notifications")),
            ],
        )

        choices.append((script_name, title, vs_alternative))
    return choices


def notification_script_title(name):
    return user_script_title("notifications", name)


def service_levels():
    try:
        return config.mkeventd_service_levels
    except:
        return [(0, "(no service level)")]


def get_vs_flexible_notifications():
    # Make sure, that list is not trivially false
    def validate_only_services(value, varprefix):
        for s in value:
            if s and s[0] != '!':
                return
        raise MKUserError(varprefix + "_0", _("The list of services will never match"))

    return CascadingDropdown(
        title=_("Notification Method"),
        choices=[
            ("email", _("Plain Text Email (using configured templates)")),
            (
                "flexible",
                _("Flexible Custom Notifications"),
                ListOf(
                    Foldable(
                        Dictionary(
                            optional_keys=[
                                "service_blacklist", "only_hosts", "only_services", "escalation",
                                "match_sl"
                            ],
                            columns=1,
                            headers=True,
                            elements=[
                                (
                                    "plugin",
                                    DropdownChoice(
                                        title=_("Notification Plugin"),
                                        choices=notification_script_choices,
                                        default_value="mail",
                                    ),
                                ),
                                ("parameters",
                                 ListOfStrings(
                                     title=_("Plugin Arguments"),
                                     help=
                                     _("You can specify arguments to the notification plugin here. "
                                       "Please refer to the documentation about the plugin for what "
                                       "parameters are allowed or required here."),
                                 )),
                                ("disabled",
                                 Checkbox(
                                     title=_("Disabled"),
                                     label=_("Currently disable this notification"),
                                     default_value=False,
                                 )),
                                ("timeperiod",
                                 cmk.gui.watolib.timeperiods.TimeperiodSelection(
                                     title=_("Timeperiod"),
                                     help=_("Do only notifiy alerts within this time period"),
                                 )),
                                (
                                    "escalation",
                                    Tuple(
                                        title=
                                        _("Restrict to n<sup>th</sup> to m<sup>th</sup> notification (escalation)"
                                         ),
                                        orientation="float",
                                        elements=[
                                            Integer(
                                                label=_("from"),
                                                help=
                                                _("Let through notifications counting from this number"
                                                 ),
                                                default_value=1,
                                                minvalue=1,
                                                maxvalue=999999,
                                            ),
                                            Integer(
                                                label=_("to"),
                                                help=
                                                _("Let through notifications counting upto this number"
                                                 ),
                                                default_value=999999,
                                                minvalue=1,
                                                maxvalue=999999,
                                            ),
                                        ],
                                    ),
                                ),
                                (
                                    "match_sl",
                                    Tuple(
                                        title=_("Match service level"),
                                        help=
                                        _("Host or Service must be in the following service level to get notification"
                                         ),
                                        orientation="horizontal",
                                        show_titles=False,
                                        elements=[
                                            DropdownChoice(
                                                label=_("from:"),
                                                choices=service_levels,
                                                prefix_values=True),
                                            DropdownChoice(
                                                label=_(" to:"),
                                                choices=service_levels,
                                                prefix_values=True),
                                        ],
                                    ),
                                ),
                                ("host_events",
                                 ListChoice(
                                     title=_("Host Events"),
                                     choices=[
                                         ('d', _("Host goes down")),
                                         ('u', _("Host gets unreachble")),
                                         ('r', _("Host goes up again")),
                                         ('f', _("Start or end of flapping state")),
                                         ('s', _("Start or end of a scheduled downtime ")),
                                         ('x', _("Acknowledgement of host problem")),
                                     ],
                                     default_value=['d', 'u', 'r', 'f', 's', 'x'],
                                 )),
                                ("service_events",
                                 ListChoice(
                                     title=_("Service Events"),
                                     choices=[
                                         ('w', _("Service goes into warning state")),
                                         ('u', _("Service goes into unknown state")),
                                         ('c', _("Service goes into critical state")),
                                         ('r', _("Service recovers to OK")),
                                         ('f', _("Start or end of flapping state")),
                                         ('s', _("Start or end of a scheduled downtime")),
                                         ('x', _("Acknowledgement of service problem")),
                                     ],
                                     default_value=['w', 'c', 'u', 'r', 'f', 's', 'x'],
                                 )),
                                (
                                    "only_hosts",
                                    ListOfStrings(
                                        title=_("Limit to the following hosts"),
                                        help=
                                        _("Configure the hosts for this notification. Without prefix, only exact, case sensitive matches, "
                                          "<tt>!</tt> for negation and <tt>~</tt> for regex matches."
                                         ),
                                        orientation="horizontal",
                                        # TODO: Clean this up to use an alternative between TextAscii() and RegExp(). Also handle the negation in a different way
                                        valuespec=TextAscii(size=20,),
                                    ),
                                ),
                                (
                                    "only_services",
                                    ListOfStrings(
                                        title=_("Limit to the following services"),
                                        help=
                                        _("Configure regular expressions that match the beginning of the service names here. Prefix an "
                                          "entry with <tt>!</tt> in order to <i>exclude</i> that service."
                                         ),
                                        orientation="horizontal",
                                        # TODO: Clean this up to use an alternative between TextAscii() and RegExp(). Also handle the negation in a different way
                                        valuespec=TextAscii(size=20,),
                                        validate=validate_only_services,
                                    ),
                                ),
                                (
                                    "service_blacklist",
                                    ListOfStrings(
                                        title=_("Blacklist the following services"),
                                        help=
                                        _("Configure regular expressions that match the beginning of the service names here."
                                         ),
                                        orientation="horizontal",
                                        valuespec=RegExp(
                                            size=20,
                                            mode=RegExp.prefix,
                                        ),
                                        validate=validate_only_services,
                                    ),
                                ),
                            ]),
                        title_function=
                        lambda v: _("Notify by: ") + notification_script_title(v["plugin"]),
                    ),
                    title=_("Flexible Custom Notifications"),
                    add_label=_("Add notification"),
                ),
            ),
        ])


def get_vs_notification_methods():
    return CascadingDropdown(
        title=_("Notification Method"),
        choices=notification_script_choices_with_parameters,
        default_value=("mail", {}))


def get_vs_user_idle_timeout():
    return Alternative(
        title=_("Session idle timeout"),
        elements=[
            FixedValue(
                None,
                title=_("Use the global configuration"),
                totext="",
            ),
            FixedValue(
                False,
                title=_("Disable the login timeout"),
                totext="",
            ),
            Age(
                title=_("Set an individual idle timeout"),
                display=["minutes", "hours", "days"],
                minvalue=60,
                default_value=3600,
            ),
        ],
        style="dropdown",
        orientation="horizontal",
    )


def validate_user_attributes(all_users, user_id, user_attrs, is_new_user=True):
    # Check user_id
    if is_new_user:
        if user_id in all_users:
            raise MKUserError("user_id", _("This username is already being used by another user."))
        vs_user_id = UserID(allow_empty=False)
        vs_user_id.validate_value(user_id, "user_id")
    else:
        if user_id not in all_users:
            raise MKUserError(None, _("The user you are trying to edit does not exist."))

    # Full name
    alias = user_attrs.get("alias")
    if not alias:
        raise MKUserError("alias",
                          _("Please specify a full name or descriptive alias for the user."))

    # Locking
    locked = user_attrs.get("locked")
    if user_id == config.user.id and locked:
        raise MKUserError("locked", _("You cannot lock your own account!"))

    # Authentication: Password or Secret
    if "automation_secret" in user_attrs:
        secret = user_attrs["automation_secret"]
        if len(secret) < 10:
            raise MKUserError('secret',
                              _("Please specify a secret of at least 10 characters length."))
    else:
        password = user_attrs.get("password")
        if password:
            verify_password_policy(password)

    # Email
    email = user_attrs.get("email")
    vs_email = EmailAddressUnicode()
    vs_email.validate_value(email, "email")

    # Idle timeout
    idle_timeout = user_attrs.get("idle_timeout")
    vs_user_idle_timeout = get_vs_user_idle_timeout()
    vs_user_idle_timeout.validate_value(idle_timeout, "idle_timeout")

    # Notification settings are only active if we do *not* have rule based notifications!
    rulebased_notifications = load_configuration_settings().get("enable_rulebased_notifications")
    if not rulebased_notifications:
        # Notifications
        notifications_enabled = user_attrs.get("notification_enabled")

        # Check if user can receive notifications
        if notifications_enabled:
            if not email:
                raise MKUserError(
                    "email",
                    _('You have enabled the notifications but missed to configure a '
                      'Email address. You need to configure your mail address in order '
                      'to be able to receive emails.'))

            contactgroups = user_attrs.get("contactgroups")
            if not contactgroups:
                raise MKUserError(
                    "notifications_enabled",
                    _('You have enabled the notifications but missed to make the '
                      'user member of at least one contact group. You need to make '
                      'the user member of a contact group which has hosts assigned '
                      'in order to be able to receive emails.'))

            roles = user_attrs.get("roles")
            if not roles:
                raise MKUserError("role_user",
                                  _("Your user has no roles. Please assign at least one role."))

        notification_method = user_attrs.get("notification_method")
        get_vs_flexible_notifications().validate_value(notification_method, "notification_method")
    else:
        fallback_contact = user_attrs.get("fallback_contact")
        if fallback_contact and not email:
            raise MKUserError(
                "email",
                _("You have enabled the fallback notifications but missed to configure an "
                  "email address. You need to configure your mail address in order "
                  "to be able to receive fallback notifications."))

    # Custom user attributes
    for name, attr in userdb.get_user_attributes():
        value = user_attrs.get(name)
        attr.valuespec().validate_value(value, "ua_" + name)


def delete_users(users_to_delete):
    if config.user.id in users_to_delete:
        raise MKUserError(None, _("You cannot delete your own account!"))

    all_users = userdb.load_users(lock=True)

    deleted_users = []
    for entry in users_to_delete:
        if entry in all_users:  # Silently ignore not existing users
            deleted_users.append(entry)
            del all_users[entry]
        else:
            raise MKUserError(None, _("Unknown user: %s") % entry)

    if deleted_users:
        add_change("edit-users", _("Deleted user: %s") % ", ".join(deleted_users))
        userdb.save_users(all_users)


def edit_users(changed_users):
    all_users = userdb.load_users(lock=True)
    new_users_info = []
    modified_users_info = []
    for user_id, settings in changed_users.items():
        user_attrs = settings.get("attributes")
        is_new_user = settings.get("is_new_user", True)
        validate_user_attributes(all_users, user_id, user_attrs, is_new_user=is_new_user)
        if is_new_user:
            new_users_info.append(user_id)
        else:
            modified_users_info.append(user_id)

        all_users[user_id] = user_attrs

    if new_users_info:
        add_change("edit-users", _("Created new user: %s") % ", ".join(new_users_info))
    if modified_users_info:
        add_change("edit-users", _("Modified user: %s") % ", ".join(modified_users_info))

    userdb.save_users(all_users)


#.
#   .--Network Scan--------------------------------------------------------.
#   |   _   _      _                      _      ____                      |
#   |  | \ | | ___| |___      _____  _ __| | __ / ___|  ___ __ _ _ __      |
#   |  |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / \___ \ / __/ _` | '_ \     |
#   |  | |\  |  __/ |_ \ V  V / (_) | |  |   <   ___) | (_| (_| | | | |    |
#   |  |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\ |____/ \___\__,_|_| |_|    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The WATO folders network scan for new hosts.                         |
#   '----------------------------------------------------------------------'

NetworkScanRequest = NamedTuple("NetworkScanRequest", [("folder_path", str)])


@automation_command_registry.register
class AutomationNetworkScan(AutomationCommand):
    def command_name(self):
        return "network-scan"

    def get_request(self):
        # type: () -> NetworkScanRequest
        folder_path = html.request.var("folder")
        if folder_path is None:
            raise MKGeneralException(_("Folder path is missing"))
        return NetworkScanRequest(folder_path=folder_path)

    def execute(self, request):
        folder = Folder.folder(request.folder_path)
        return do_network_scan(folder)


# This is executed in the site the host is assigned to.
# A list of tuples is returned where each tuple represents a new found host:
# [(hostname, ipaddress), ...]
def do_network_scan(folder):
    ip_addresses = _ip_addresses_to_scan(folder)
    return _scan_ip_addresses(folder, ip_addresses)


def _ip_addresses_to_scan(folder):
    ip_range_specs = folder.attribute("network_scan")["ip_ranges"]
    exclude_specs = folder.attribute("network_scan")["exclude_ranges"]

    to_scan = _ip_addresses_of_ranges(ip_range_specs)
    exclude = _ip_addresses_of_ranges(exclude_specs)

    # Remove excludes from to_scan list
    to_scan.difference_update(exclude)

    # Reduce by all known host addresses
    # FIXME/TODO: Shouldn't this filtering be done on the central site?
    to_scan.difference_update(_known_ip_addresses())

    # And now apply the IP regex patterns to exclude even more addresses
    to_scan.difference_update(_excludes_by_regexes(to_scan, exclude_specs))

    return to_scan


def _ip_addresses_of_ranges(ip_ranges):
    addresses = set([])

    for ty, spec in ip_ranges:
        if ty == "ip_range":
            addresses.update(_ip_addresses_of_range(spec))

        elif ty == "ip_network":
            addresses.update(_ip_addresses_of_network(spec))

        elif ty == "ip_list":
            addresses.update(spec)

    return addresses


FULL_IPV4 = (2**32) - 1


def _ip_addresses_of_range(spec):
    first_int, last_int = map(_ip_int_from_string, spec)

    addresses = []

    if first_int > last_int:
        return addresses  # skip wrong config

    while first_int <= last_int:
        addresses.append(_string_from_ip_int(first_int))
        first_int += 1
        if first_int - 1 == FULL_IPV4:  # stop on last IPv4 address
            break

    return addresses


def _ip_int_from_string(ip_str):
    packed_ip = 0
    octets = ip_str.split(".")
    for oc in octets:
        packed_ip = (packed_ip << 8) | int(oc)
    return packed_ip


def _string_from_ip_int(ip_int):
    octets = []
    for _ in xrange(4):
        octets.insert(0, str(ip_int & 0xFF))
        ip_int >>= 8
    return ".".join(octets)


def _ip_addresses_of_network(spec):
    net_addr, net_bits = spec

    ip_int = _ip_int_from_string(net_addr)
    mask_int = _mask_bits_to_int(int(net_bits))
    first = ip_int & (FULL_IPV4 ^ mask_int)
    last = ip_int | (1 << (32 - int(net_bits))) - 1

    return [_string_from_ip_int(i) for i in range(first + 1, last - 1)]


def _mask_bits_to_int(n):
    return (1 << (32 - n)) - 1


# This will not scale well. Do you have a better idea?
def _known_ip_addresses():
    addresses = (host.attribute("ipaddress") for host in Host.all().itervalues())
    return [address for address in addresses if address]


def _excludes_by_regexes(addresses, exclude_specs):
    patterns = []
    for ty, spec in exclude_specs:
        if ty == "ip_regex_list":
            for p in spec:
                patterns.append(re.compile(p))

    if not patterns:
        return []

    excludes = []
    for address in addresses:
        for p in patterns:
            if p.match(address):
                excludes.append(address)
                break  # one match is enough, exclude this.

    return excludes


# Start ping threads till max parallel pings let threads do their work till all are done.
# let threds also do name resolution. Return list of tuples (hostname, address).
def _scan_ip_addresses(folder, ip_addresses):
    num_addresses = len(ip_addresses)

    # dont start more threads than needed
    parallel_pings = min(
        folder.attribute("network_scan").get("max_parallel_pings", 100), num_addresses)

    # Initalize all workers
    threads = []
    found_hosts = []
    for _t_num in range(parallel_pings):
        t = threading.Thread(target=_ping_worker, args=[ip_addresses, found_hosts])
        t.daemon = True
        threads.append(t)
        t.start()

    # Now wait for all workers to finish
    for t in threads:
        t.join()

    return found_hosts


def _ping_worker(addresses, hosts):
    while True:
        try:
            ipaddress = addresses.pop()
        except KeyError:
            break

        if _ping(ipaddress):
            try:
                host_name = socket.gethostbyaddr(ipaddress)[0]
            except socket.error:
                host_name = ipaddress

            hosts.append((host_name, ipaddress))


def _ping(address):
    return subprocess.Popen(['ping', '-c2', '-w2', address],
                            stdout=open(os.devnull, "a"),
                            stderr=subprocess.STDOUT,
                            close_fds=True).wait() == 0


#.
#   .--MIXED STUFF---------------------------------------------------------.
#   |     __  __ _____  _______ ____    ____ _____ _   _ _____ _____       |
#   |    |  \/  |_ _\ \/ / ____|  _ \  / ___|_   _| | | |  ___|  ___|      |
#   |    | |\/| || | \  /|  _| | | | | \___ \ | | | | | | |_  | |_         |
#   |    | |  | || | /  \| |___| |_| |  ___) || | | |_| |  _| |  _|        |
#   |    |_|  |_|___/_/\_\_____|____/  |____/ |_|  \___/|_|   |_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | CLEAN THIS UP LATER                                                  |
#   '----------------------------------------------------------------------'


class WatoSimpleConfigFile(object):
    """Manage simple .mk config file containing a single dict variable

    The file handling logic is inherited from cmk.utils.store.load_from_mk_file()
    and cmk.utils.store.save_to_mk_file().
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, config_file_path, config_variable):
        # type: (Path, str) -> None
        self._config_file_path = config_file_path
        self._config_variable = config_variable

    def load_for_reading(self):
        return self._load_file(lock=False)

    def load_for_modification(self):
        return self._load_file(lock=True)

    def _load_file(self, lock=False):
        return cmk.utils.store.load_from_mk_file(
            "%s" % self._config_file_path, key=self._config_variable, default={}, lock=lock)

    def save(self, cfg):
        # Should be fixed when using pylint 2.0 (https://github.com/PyCQA/pylint/issues/1660)
        self._config_file_path.parent.mkdir(mode=0770, exist_ok=True)  # pylint: disable=no-member
        cmk.utils.store.save_to_mk_file("%s" % self._config_file_path, self._config_variable, cfg)

    def filter_usable_entries(self, entries):
        return entries

    def filter_editable_entries(self, entries):
        return entries


class PasswordStore(WatoSimpleConfigFile):
    def __init__(self):
        super(PasswordStore, self).__init__(
            config_file_path=Path(wato_root_dir) / "passwords.mk",
            config_variable="stored_passwords")

    def filter_usable_entries(self, entries):
        if config.user.may("wato.edit_all_passwords"):
            return entries

        user_groups = userdb.contactgroups_of_user(config.user.id)

        passwords = self.filter_editable_entries(entries)
        passwords.update(
            dict([(k, v) for k, v in entries.items() if v["shared_with"] in user_groups]))
        return passwords

    def filter_editable_entries(self, entries):
        if config.user.may("wato.edit_all_passwords"):
            return entries

        user_groups = userdb.contactgroups_of_user(config.user.id)
        return dict([(k, v) for k, v in entries.items() if v["owned_by"] in user_groups])


class UserSelection(DropdownChoice):
    """Dropdown for choosing a multisite user"""

    def __init__(self, **kwargs):
        only_contacts = kwargs.get("only_contacts", False)
        kwargs["choices"] = self._generate_wato_users_elements_function(
            kwargs.get("none"), only_contacts=only_contacts)
        kwargs["invalid_choice"] = "complain"  # handle vanished users correctly!
        DropdownChoice.__init__(self, **kwargs)

    def _generate_wato_users_elements_function(self, none_value, only_contacts=False):
        def get_wato_users(nv):
            users = userdb.load_users()
            elements = [(name, "%s - %s" % (name, us.get("alias", name)))
                        for (name, us) in users.items()
                        if (not only_contacts or us.get("contactgroups"))]
            elements.sort()
            if nv is not None:
                elements = [(None, none_value)] + elements
            return elements

        return lambda: get_wato_users(none_value)

    def value_to_text(self, value):
        text = DropdownChoice.value_to_text(self, value)
        return text.split(" - ")[-1]


def multifolder_host_rule_match_conditions():
    return [_site_rule_match_condition(),
            _multi_folder_rule_match_condition()] + _common_host_rule_match_conditions()


def _site_rule_match_condition():
    return (
        "match_site",
        DualListChoice(
            title=_("Match site"),
            help=_("This condition makes the rule match only hosts of "
                   "the selected sites."),
            choices=config.site_attribute_choices,
        ),
    )


def _multi_folder_rule_match_condition():
    return (
        "match_folders",
        ListOf(
            FullPathFolderChoice(
                title=_("Folder"),
                help=_("This condition makes the rule match only hosts that are managed "
                       "via WATO and that are contained in this folder - either directly "
                       "or in one of its subfolders."),
            ),
            add_label=_("Add additional folder"),
            title=_("Match folders"),
            movable=False),
    )


def _common_host_rule_match_conditions():
    return [
        ("match_hosttags", HostTagCondition(title=_("Match Host Tags"))),
        ("match_hostgroups",
         userdb.GroupChoice(
             "host",
             title=_("Match Host Groups"),
             help=_("The host must be in one of the selected host groups"),
             allow_empty=False,
         )),
        ("match_hosts",
         ListOfStrings(
             valuespec=MonitoredHostname(),
             title=_("Match only the following hosts"),
             size=24,
             orientation="horizontal",
             allow_empty=False,
             empty_text=
             _("Please specify at least one host. Disable the option if you want to allow all hosts."
              ),
         )),
        ("match_exclude_hosts",
         ListOfStrings(
             valuespec=MonitoredHostname(),
             title=_("Exclude the following hosts"),
             size=24,
             orientation="horizontal",
         ))
    ]


def simple_host_rule_match_conditions():
    return [_site_rule_match_condition(),
            _single_folder_rule_match_condition()] + _common_host_rule_match_conditions()


def _single_folder_rule_match_condition():
    return (
        "match_folder",
        FolderChoice(
            title=_("Match folder"),
            help=_("This condition makes the rule match only hosts that are managed "
                   "via WATO and that are contained in this folder - either directly "
                   "or in one of its subfolders."),
        ),
    )


class FolderChoice(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs["choices"] = Folder.folder_choices
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


class FullPathFolderChoice(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs["choices"] = Folder.folder_choices_fulltitle
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


def transform_simple_to_multi_host_rule_match_conditions(value):
    if value and "match_folder" in value:
        value["match_folders"] = [value.pop("match_folder")]
    return value


class WatoBackgroundProcess(gui_background_job.GUIBackgroundProcess):
    def initialize_environment(self):
        super(WatoBackgroundProcess, self).initialize_environment()

        if self._jobstatus.get_status().get("lock_wato"):
            cmk.utils.store.release_all_locks()
            lock_exclusive()


class WatoBackgroundJob(gui_background_job.GUIBackgroundJob):
    _background_process_class = WatoBackgroundProcess


def site_neutral_path(path):
    if path.startswith('/omd'):
        parts = path.split('/')
        parts[3] = '[SITE_ID]'
        return '/'.join(parts)
    return path


# Checks if a valuespec is a Checkbox
def is_a_checkbox(vs):
    if isinstance(vs, Checkbox):
        return True
    elif isinstance(vs, Transform):
        return is_a_checkbox(vs._valuespec)
    return False


def get_search_expression():
    search = html.get_unicode_input("search")
    if search is not None:
        search = search.strip().lower()
    return search


def make_action_link(vars_):
    return folder_preserving_link(vars_ + [("_transid", html.transaction_manager.get())])


def may_edit_configvar(varname):
    if varname in ["actions"]:
        return config.user.may("wato.add_or_modify_executables")
    return True


# TODO: Move to Folder()?
def check_wato_foldername(htmlvarname, name, just_name=False):
    if not just_name and Folder.current().has_subfolder(name):
        raise MKUserError(htmlvarname, _("A folder with that name already exists."))

    if not name:
        raise MKUserError(htmlvarname, _("Please specify a name."))

    if not re.match("^[-a-z0-9A-Z_]*$", name):
        raise MKUserError(
            htmlvarname,
            _("Invalid folder name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))


# TODO: Move to Folder()?
def create_wato_foldername(title, in_folder=None):
    if in_folder is None:
        in_folder = Folder.current()

    basename = convert_title_to_filename(title)
    c = 1
    name = basename
    while True:
        if not in_folder.has_subfolder(name):
            break
        c += 1
        name = "%s-%d" % (basename, c)
    return name


# TODO: Move to Folder()?
def convert_title_to_filename(title):
    converted = ""
    for c in title.lower():
        if c == u'ä':
            converted += 'ae'
        elif c == u'ö':
            converted += 'oe'
        elif c == u'ü':
            converted += 'ue'
        elif c == u'ß':
            converted += 'ss'
        elif c in "abcdefghijklmnopqrstuvwxyz0123456789-_":
            converted += c
        else:
            converted += "_"
    return str(converted)


# TODO: Deprecate this legacy format with 1.4.0 or later?!
def mk_eval(s):
    try:
        if not config.wato_legacy_eval:
            return ast.literal_eval(base64.b64decode(s))
        return pickle.loads(base64.b64decode(s))
    except:
        raise MKGeneralException(_('Unable to parse provided data: %s') % html.render_text(repr(s)))


def get_hostnames_from_checkboxes(filterfunc=None):
    """Create list of all host names that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    show_checkboxes = html.request.var("show_checkboxes") == "1"
    if show_checkboxes:
        selected = weblib.get_rowselection('wato-folder-/' + Folder.current().path())
    search_text = html.request.var("search")

    selected_host_names = []
    for host_name, host in sorted(Folder.current().hosts().items()):
        if (not search_text or (search_text.lower() in host_name.lower())) \
            and (not show_checkboxes or ('_c_' + host_name) in selected):
            if filterfunc is None or \
               filterfunc(host):
                selected_host_names.append(host_name)
    return selected_host_names


def get_hosts_from_checkboxes(filterfunc=None):
    """Create list of all host objects that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    folder = Folder.current()
    return [folder.host(host_name) for host_name in get_hostnames_from_checkboxes(filterfunc)]


def rule_option_elements(disabling=True):
    elements = [
        ("description",
         TextUnicode(
             title=_("Description"),
             help=_("A description or title of this rule"),
             size=80,
         )),
        ("comment", RuleComment()),
        ("docu_url", DocumentationURL()),
    ]
    if disabling:
        elements += [
            ("disabled",
             Checkbox(
                 title=_("Rule activation"),
                 help=_("Disabled rules are kept in the configuration but are not applied."),
                 label=_("do not apply this rule"),
             )),
        ]
    return elements


def DocumentationURL():
    return TextAscii(
        title=_("Documentation URL"),
        help=HTML(
            _("An optional URL pointing to documentation or any other page. This will be displayed "
              "as an icon %s and open a new page when clicked. "
              "You can use either global URLs (beginning with <tt>http://</tt>), absolute local urls "
              "(beginning with <tt>/</tt>) or relative URLs (that are relative to <tt>check_mk/</tt>)."
             ) % html.render_icon("url")),
        size=80,
    )


class ConfigHostname(TextAsciiAutocomplete):
    """Hostname input with dropdown completion

    Renders an input field for entering a host name while providing an auto completion dropdown field.
    Fetching the choices from the current WATO config"""
    ident = "monitored_hostname"

    def __init__(self, **kwargs):
        super(ConfigHostname, self).__init__(
            completion_ident=self.ident, completion_params={}, **kwargs)

    @classmethod
    def autocomplete_choices(cls, value, params):
        """Return the matching list of dropdown choices
        Called by the webservice with the current input field value and the completions_params to get the list of choices"""
        all_hosts = Host.all()
        match_pattern = re.compile(value, re.IGNORECASE)
        return [(h, h) for h in all_hosts.keys() if match_pattern.search(h) is not None]
