#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
import traceback
from typing import Any, Dict
from typing import Optional as _Optional

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import ConfigurationWarnings

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.wato.utils import (
    ABCConfigDomain,
    config_domain_registry,
    config_variable_registry,
    ConfigDomainOMD,
    ConfigVariable,
    ConfigVariableGroupSiteManagement,
    LivestatusViaTCP,
    ReplicationPath,
    wato_fileheader,
)
from cmk.gui.plugins.watolib.utils import SerializedSettings
from cmk.gui.type_defs import ConfigDomainName
from cmk.gui.valuespec import (
    Age,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Filesize,
    Integer,
    ListChoice,
    Optional,
    Tuple,
)
from cmk.gui.watolib.activate_changes import add_replication_paths

# .
#   .--omd config----------------------------------------------------------.
#   |                             _                    __ _                |
#   |          ___  _ __ ___   __| |   ___ ___  _ __  / _(_) __ _          |
#   |         / _ \| '_ ` _ \ / _` |  / __/ _ \| '_ \| |_| |/ _` |         |
#   |        | (_) | | | | | | (_| | | (_| (_) | | | |  _| | (_| |         |
#   |         \___/|_| |_| |_|\__,_|  \___\___/|_| |_|_| |_|\__, |         |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+
#   | Settings managed via "omd config"                                    |
#   '----------------------------------------------------------------------'


@config_variable_registry.register
class ConfigVariableSiteAutostart(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainOMD

    def ident(self):
        return "site_autostart"

    def valuespec(self):
        return Checkbox(
            title=_("Start during system boot"),
            help=_(
                "Whether or not this site should be started during startup of "
                "the Check_MK server."
            ),
        )


@config_variable_registry.register
class ConfigVariableSiteCore(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainOMD

    def ident(self):
        return "site_core"

    def valuespec(self):
        return DropdownChoice(
            title=_("Monitoring core"),
            help=_(
                "Choose the monitoring core to run for monitoring. You can also "
                "decide to run no monitoring core in this site. This can be useful "
                "for instances running only a GUI for connecting to other monitoring "
                "sites."
            ),
            choices=self._monitoring_core_choices(),
        )

    def _monitoring_core_choices(self):
        cores = []
        if not cmk_version.is_raw_edition():
            cores.append(("cmc", _("Checkmk Micro Core")))

        cores += [
            ("nagios", _("Nagios 3")),
            ("none", _("No monitoring core")),
        ]

        return cores


@config_variable_registry.register
class ConfigVariableSiteLivestatusTCP(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainOMD

    def ident(self):
        return "site_livestatus_tcp"

    def valuespec(self):
        return Optional(
            valuespec=LivestatusViaTCP(),
            title=_("Access to Livestatus via TCP"),
            help=_(
                "Check_MK Livestatus usually listens only on a local UNIX socket - "
                "for reasons of performance and security. This option is used "
                "to make it reachable via TCP on a port configurable with LIVESTATUS_TCP_PORT."
            ),
            label=_("Enable Livestatus access via network (TCP)"),
            none_label=_("Livestatus is available locally"),
        )


@config_variable_registry.register
class ConfigVariableSiteEventConsole(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainOMD

    def ident(self):
        return "site_mkeventd"

    def valuespec(self):
        return Optional(
            valuespec=ListChoice(
                choices=[
                    ("SNMPTRAP", _("Receive SNMP traps (UDP/162)")),
                    ("SYSLOG", _("Receive Syslog messages (UDP/514)")),
                    ("SYSLOG_TCP", _("Receive Syslog messages (TCP/514)")),
                ],
                title=_("Listen for incoming messages via"),
                empty_text=_("Locally enabled"),
            ),
            title=_("Event Console"),
            help=_(
                "This option enables the Event Console - The event processing and "
                "classification daemon of Check_MK. You can also configure whether "
                "or not the Event Console shal listen for incoming SNMP traps or "
                "syslog messages. Please note that only a single Check_MK site per "
                "Check_MK server can listen for such messages."
            ),
            label=_("Event Console enabled"),
            none_label=_("Event Console disabled"),
            indent=False,
        )


# .
#   .--Diskspace-----------------------------------------------------------.
#   |              ____  _     _                                           |
#   |             |  _ \(_)___| | _____ _ __   __ _  ___ ___               |
#   |             | | | | / __| |/ / __| '_ \ / _` |/ __/ _ \              |
#   |             | |_| | \__ \   <\__ \ |_) | (_| | (_|  __/              |
#   |             |____/|_|___/_|\_\___/ .__/ \__,_|\___\___|              |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   | Management of the disk space cleanup settings                        |
#   '----------------------------------------------------------------------'


# TODO: Diskspace cleanup does not support site specific globals!
@config_domain_registry.register
class ConfigDomainDiskspace(ABCConfigDomain):
    needs_sync = True
    needs_activation = False
    diskspace_config = cmk.utils.paths.omd_root / "etc/diskspace.conf"

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "diskspace"

    def activate(self, settings: _Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        return []

    def config_dir(self):
        return ""  # unused, we override load and save below

    def load_full_config(self, site_specific=False, custom_site_path=None):
        return self.load()

    def load(self, site_specific=False, custom_site_path=None):
        cleanup_settings = store.load_mk_file(self.diskspace_config, default={})
        if not cleanup_settings:
            return {}

        # Convert old config (min_free_bytes and min_file_age) were independent options
        if "min_free_bytes" in cleanup_settings:
            cleanup_settings["min_free_bytes"] = (
                cleanup_settings["min_free_bytes"],
                cleanup_settings.pop("min_file_age", 2592000),
            )  # 1 month

        if cleanup_settings.get("cleanup_abandoned_host_files", False) is None:
            del cleanup_settings["cleanup_abandoned_host_files"]

        if cleanup_settings.get("max_file_age", False) is None:
            del cleanup_settings["max_file_age"]

        return {
            "diskspace_cleanup": cleanup_settings,
        }

    def save(self, settings, site_specific=False, custom_site_path=None):
        if site_specific:
            return  # not supported at the moment

        config = {}

        if "diskspace_cleanup" in settings:
            # Convert to old config format.
            for k, v in settings.get("diskspace_cleanup", {}).items():
                if k == "min_free_bytes":
                    config["min_free_bytes"], config["min_file_age"] = v
                else:
                    config[k] = v

            if "cleanup_abandoned_host_files" not in settings.get("diskspace_cleanup", {}):
                config["cleanup_abandoned_host_files"] = None

        output = ""
        for k, v in sorted(config.items()):
            output += "%s = %r\n" % (k, v)

        store.save_text_to_file(self.diskspace_config, output)

    def default_globals(self):
        diskspace_context: Dict[str, Any] = {}
        filename = cmk.utils.paths.omd_root / "bin/diskspace"
        with filename.open(encoding="utf-8") as f:
            code = compile(f.read(), str(filename), "exec")
            exec(code, {}, diskspace_context)
        return {
            "diskspace_cleanup": diskspace_context["default_config"],
        }


@config_variable_registry.register
class ConfigVariableSiteDiskspaceCleanup(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainDiskspace

    def ident(self):
        return "diskspace_cleanup"

    def valuespec(self):
        return Dictionary(
            title=_("Automatic disk space cleanup"),
            help=_(
                "You can configure your monitoring site to free disk space based on the ages "
                "of files or free space of the volume the site is placed on.<br>"
                "The monitoring site is executing the program <tt>diskspace</tt> 5 past "
                "every full hour as cron job. Details about the execution are logged to the file "
                "<tt>var/log/diskspace.log</tt>. You can always execut this program manually "
                "(add the <tt>-v</tt> option to see details about the actions taken)."
            ),
            elements=[
                (
                    "max_file_age",
                    Age(
                        minvalue=1,  # 1 sec
                        default_value=31536000,  # 1 year
                        title=_("Delete files older than"),
                        help=_(
                            "The historic events (state changes, downtimes etc.) of your hosts and services "
                            "is stored in the monitoring "
                            "history as plain text log files. One history log file contains the monitoring "
                            "history of a given time period of all hosts and services. The files which are "
                            "older than the configured time will be removed on the next execution of the "
                            "disk space cleanup.<br>"
                            "The historic metrics are stored in files for each host and service "
                            "individually. When a host or service is removed from the monitoring, it's "
                            "metric files remain untouched on your disk until the files last update "
                            "(modification time) is longer ago than the configure age."
                        ),
                    ),
                ),
                (
                    "min_free_bytes",
                    Tuple(
                        elements=[
                            Filesize(
                                title=_("Cleanup when disk space is below"),
                                minvalue=1,  # min 1 byte
                                default_value=0,
                            ),
                            Age(
                                title=_("Never remove files newer than"),
                                minvalue=1,  # minimum 1 sec
                                default_value=2592000,  # 1 month
                                help=_(
                                    "With this option you can prevent cleanup of files which have been updated "
                                    "within this time range."
                                ),
                            ),
                        ],
                        title=_("Delete additional files when disk space is below"),
                        help=_(
                            "When the disk space cleanup by file age was not able to gain enough "
                            "free disk space, then the cleanup mechanism starts cleaning up additional "
                            "files. The files are deleted by age, the oldest first, until the files are "
                            "newer than the configured minimum file age."
                        ),
                    ),
                ),
                (
                    "cleanup_abandoned_host_files",
                    Age(
                        title=_("Cleanup abandoned host files older than"),
                        minvalue=3600,  # 1 hour
                        default_value=2592000,  # 1 month
                        help=_(
                            "During monitoring there are several dedicated files created for each host. "
                            "There are, for example, the discovered services, performance data and "
                            "different temporary files created. During deletion of a host, these files "
                            "are normally deleted. But there are cases, where the files are left on "
                            "the disk until manual deletion, for example if you move a host from one "
                            "site to another or deleting a host manually from the configuration.<br>"
                            "The performance data (RRDs) and HW/SW inventory archive are never deleted "
                            "during host deletion. They are only deleted automatically when you enable "
                            "this option and after the configured period."
                        ),
                    ),
                ),
            ],
            default_keys=["cleanup_abandoned_host_files"],
            empty_text=_("Disk space cleanup is disabled"),
        )


add_replication_paths(
    [
        ReplicationPath(
            "file",
            "diskspace",
            str(ConfigDomainDiskspace.diskspace_config.relative_to(cmk.utils.paths.omd_root)),
            [],
        ),
    ]
)

# .
#   .--Apache--------------------------------------------------------------.
#   |                    _                     _                           |
#   |                   / \   _ __   __ _  ___| |__   ___                  |
#   |                  / _ \ | '_ \ / _` |/ __| '_ \ / _ \                 |
#   |                 / ___ \| |_) | (_| | (__| | | |  __/                 |
#   |                /_/   \_\ .__/ \__,_|\___|_| |_|\___|                 |
#   |                        |_|                                           |
#   +----------------------------------------------------------------------+
#   | Manage settings of the site apache                                   |
#   '----------------------------------------------------------------------'


@config_domain_registry.register
class ConfigDomainApache(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "apache"

    def config_dir(self):
        return cmk.utils.paths.default_config_dir + "/apache.d/wato/"

    def activate(self, settings: _Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        try:
            self._write_config_file()

            completed_process = subprocess.run(
                ["omd", "reload", "apache"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True,
                encoding="utf-8",
                check=False,
            )

            if completed_process.returncode:
                raise Exception(completed_process.stdout)

            return []
        except Exception:
            logger.exception("error reloading apache")
            return ["Failed to activate apache configuration: %s" % (traceback.format_exc())]

    def _write_config_file(self):
        config = self.get_effective_config()

        output = wato_fileheader()

        if config:
            output += "ServerLimit %d\n" % config["apache_process_tuning"]["number_of_processes"]
            output += "MaxClients %d\n" % config["apache_process_tuning"]["number_of_processes"]

        config_file_path = os.path.join(
            cmk.utils.paths.omd_root, "etc/apache/conf.d", "zzz_check_mk.conf"
        )
        store.save_text_to_file(config_file_path, output)

    def get_effective_config(self):
        config = self.load(site_specific=False)
        config.update(self.load(site_specific=True))
        return config

    def default_globals(self):
        return {
            "apache_process_tuning": {
                "number_of_processes": self._get_value_from_config("MaxClients", int, 64),
            }
        }

    def _get_value_from_config(self, varname, conv_func, default_value):
        config_files = [cmk.utils.paths.omd_root / "etc/apache/apache.conf"]
        config_files += sorted((cmk.utils.paths.omd_root / "etc/apache/conf.d").glob("*.conf"))

        value = default_value

        for config_file in config_files:
            if config_file.name == "zzz_check_mk.conf":
                continue  # Skip the file written by this config domain

            for line in config_file.open(encoding="utf-8"):
                if line.lstrip().startswith(varname):
                    raw_value = line.split()[1]
                    value = conv_func(raw_value)

        return value


@config_variable_registry.register
class ConfigVariableSiteApacheProcessTuning(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainApache

    def ident(self):
        return "apache_process_tuning"

    def valuespec(self):
        return Dictionary(
            title=_("Apache process tuning"),
            elements=[
                (
                    "number_of_processes",
                    Integer(
                        title=_("Number of apache processes"),
                        help=_(
                            "Use this value to tune the maximum number of apache client requests that will be processed simultaneously "
                            "(maximum number of apache server processes allowed to start). In case you have a lot of incoming "
                            "requests in parallel it may be a good idea to increase this value. But do this carefully, more is "
                            "not always better. The apache processes normally need a decent amount of memory and you should "
                            "only configure as many apache processes as your system can handle in high load situations."
                        ),
                        minvalue=5,
                    ),
                ),
            ],
        )


# .
#   .--rrdcached-----------------------------------------------------------.
#   |                        _                _              _             |
#   |           _ __ _ __ __| | ___ __ _  ___| |__   ___  __| |            |
#   |          | '__| '__/ _` |/ __/ _` |/ __| '_ \ / _ \/ _` |            |
#   |          | |  | | | (_| | (_| (_| | (__| | | |  __/ (_| |            |
#   |          |_|  |_|  \__,_|\___\__,_|\___|_| |_|\___|\__,_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Use these options to tune the performance of the rrdcached           |
#   '----------------------------------------------------------------------'


@config_domain_registry.register
class ConfigDomainRRDCached(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "rrdcached"

    def config_dir(self):
        return cmk.utils.paths.default_config_dir + "/rrdcached.d/wato/"

    def activate(self, settings: _Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        try:
            self._write_config_file()

            completed_process = subprocess.run(
                ["omd", "restart", "rrdcached"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True,
                encoding="utf-8",
                check=False,
            )

            if completed_process.returncode:
                raise Exception(completed_process.stdout)

            return []
        except Exception:
            logger.exception("error restarting rrdcached")
            return ["Failed to activate rrdcached configuration: %s" % (traceback.format_exc())]

    def _write_config_file(self):
        config = self._get_effective_config()

        output = wato_fileheader()
        for key, val in sorted(config.get("rrdcached_tuning", {}).items()):
            output += "%s=%d\n" % (key, val)

        config_file_path = os.path.join(
            cmk.utils.paths.omd_root, "etc/rrdcached.d", "zzz_check_mk.conf"
        )
        store.save_text_to_file(config_file_path, output)

    def _get_effective_config(self):
        config = self.load(site_specific=False)
        config.update(self.load(site_specific=True))
        return config

    def default_globals(self):
        return {
            "rrdcached_tuning": {
                "TIMEOUT": self._get_value_from_config("TIMEOUT", int, 3600),
                "RANDOM_DELAY": self._get_value_from_config("RANDOM_DELAY", int, 1800),
                "FLUSH_TIMEOUT": self._get_value_from_config("FLUSH_TIMEOUT", int, 7200),
                "WRITE_THREADS": self._get_value_from_config("WRITE_THREADS", int, 4),
            }
        }

    def _get_value_from_config(self, varname, conv_func, default_value):
        config_files = [cmk.utils.paths.omd_root / "etc/rrdcached.conf"]
        config_files += sorted((cmk.utils.paths.omd_root / "etc/rrdcached.d").glob("*.conf"))

        value = default_value

        for config_file in config_files:
            if config_file.name == "zzz_check_mk.conf":
                continue  # Skip the file written by this config domain

            for line in config_file.open(encoding="utf-8"):
                if line.lstrip().startswith(varname):
                    raw_value = line.split("=")[1]
                    value = conv_func(raw_value)

        return value


@config_variable_registry.register
class ConfigVariableSiteRRDCachedTuning(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainRRDCached

    def ident(self):
        return "rrdcached_tuning"

    def valuespec(self):
        return Dictionary(
            title=_("RRDCached tuning"),
            elements=[
                (
                    "TIMEOUT",
                    Age(
                        title=_("Disk flush interval of updated metrics"),
                        help=_(
                            "Updated metrics are written to disk in the configured interval. "
                            "The write operation is only performed for metrics that are being "
                            "updated. Old metrics are not affected by this option."
                        ),
                        minvalue=0,
                    ),
                ),
                (
                    "RANDOM_DELAY",
                    Age(
                        title=_("Random delay"),
                        help=_(
                            "The rrdcached will delay writing of each metric for a random "
                            "number of seconds in the range [0..delay]. This will avoid too many "
                            "writes being queued simultaneously. This number should not be "
                            'higher than the value specified in "Disk flush interval of '
                            'updated metrics".'
                        ),
                        minvalue=0,
                    ),
                ),
                (
                    "FLUSH_TIMEOUT",
                    Age(
                        title=_("Disk flush interval of old data"),
                        help=_(
                            "The entire cache is searched in the interval configured here for old "
                            "values which shal be written to disk. This only concerns RRD files to "
                            "which updates have stopped, so setting this to a high value is "
                            "acceptable in most cases."
                        ),
                        minvalue=0,
                    ),
                ),
                (
                    "WRITE_THREADS",
                    Integer(
                        title=_("Number of threads used for writing RRD files"),
                        help=_(
                            "Increasing this number will allow rrdcached to have more simultaneous "
                            "I/O requests into the kernel. This may allow the kernel to re-order "
                            "disk writes, resulting in better disk throughput."
                        ),
                        minvalue=1,
                        maxvalue=100,
                    ),
                ),
            ],
            optional_keys=[],
        )
