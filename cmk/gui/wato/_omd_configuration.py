#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import subprocess
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import override, TypeVar

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.version import Edition
from cmk.diskspace.config import DEFAULT_CONFIG as diskspace_DEFAULT_CONFIG
from cmk.gui.form_specs.generators.age import Age as FSAge
from cmk.gui.form_specs.unstable.legacy_converter import Tuple as FSTuple
from cmk.gui.log import logger
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.wato._livestatus import ConfigVariableSiteLivestatusTCP
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigDomainRegistry,
    ConfigVariable,
    ConfigVariableRegistry,
    GlobalSettingsContext,
    SerializedSettings,
    wato_fileheader,
)
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.config_sync import (
    ReplicationPath,
    ReplicationPathRegistry,
    ReplicationPathType,
)
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSiteManagement
from cmk.rulesets.internal.form_specs import (
    DictionaryExtended,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    IECMagnitude,
    Integer,
    validators,
)
from cmk.utils.config_warnings import ConfigurationWarnings

T = TypeVar("T")

FILESIZE_MAGNITUDES = [
    IECMagnitude.BYTE,
    IECMagnitude.KIBI,
    IECMagnitude.MEBI,
    IECMagnitude.GIBI,
    IECMagnitude.TEBI,
]


def register(
    config_domain_registry: ConfigDomainRegistry,
    config_variable_registry: ConfigVariableRegistry,
    replication_path_registry: ReplicationPathRegistry,
) -> None:
    config_domain_registry.register(ConfigDomainDiskspace())
    config_domain_registry.register(ConfigDomainApache())
    config_domain_registry.register(ConfigDomainRRDCached())
    config_variable_registry.register(ConfigVariableSiteAutostart)
    config_variable_registry.register(ConfigVariableSiteCore)
    config_variable_registry.register(ConfigVariableSiteLivestatusTCP)
    config_variable_registry.register(ConfigVariableSiteDiskspaceCleanup)
    config_variable_registry.register(ConfigVariableSiteApacheProcessTuning)
    config_variable_registry.register(ConfigVariableSiteRRDCachedTuning)
    replication_path_registry.register(
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="diskspace",
            site_path=str(
                cmk.utils.paths.diskspace_config_dir.relative_to(cmk.utils.paths.omd_root)
            ),
        )
    )


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


ConfigVariableSiteAutostart = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainOMD,
    ident="site_autostart",
    form_spec=lambda context: BooleanChoice(
        title=Title("Start during system boot"),
        help_text=Help(
            "Whether or not this site should be started during startup of the Checkmk server."
        ),
    ),
)


def _form_spec_site_core(context: GlobalSettingsContext) -> SingleChoiceExtended[str]:
    choices = _monitoring_core_choices(context.edition_of_local_site)
    return SingleChoiceExtended[str](
        title=Title("Monitoring core"),
        help_text=Help(
            "Choose the monitoring core to run for monitoring. You can also "
            "decide to run no monitoring core in this site. This can be useful "
            "for instances running only a GUI for connecting to other monitoring "
            "sites."
        ),
        elements=[SingleChoiceElementExtended(name=name, title=title) for name, title in choices],
        prefill=DefaultValue(choices[0][0]),
    )


ConfigVariableSiteCore = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainOMD,
    ident="site_core",
    form_spec=_form_spec_site_core,
)


def _monitoring_core_choices(edition: Edition) -> list[tuple[str, Title]]:
    cores = []
    if edition is not Edition.COMMUNITY:
        cores.append(("cmc", Title("Checkmk Micro Core")))

    cores += [
        ("nagios", Title("Nagios 3")),
        ("none", Title("No monitoring core")),
    ]

    return cores


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


class ConfigDomainDiskspace(ABCConfigDomain):
    needs_sync = True
    needs_activation = False

    @classmethod
    @override
    def ident(cls) -> ConfigDomainName:
        return "diskspace"

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def config_dir(self) -> Path:
        return cmk.utils.paths.diskspace_config_dir

    @override
    def default_globals(self) -> GlobalSettings:
        return {"diskspace_cleanup": diskspace_DEFAULT_CONFIG.model_dump(exclude_none=True)}


ConfigVariableSiteDiskspaceCleanup = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainDiskspace,
    ident="diskspace_cleanup",
    form_spec=lambda context: DictionaryExtended(
        default_checked=["cleanup_abandoned_host_files"],
        title=Title("Automatic disk space cleanup"),
        help_text=Help(
            "You can configure your monitoring site to free disk space based on the ages "
            "of files or free space of the volume the site is placed on.<br>"
            "The monitoring site is executing the program <tt>diskspace</tt> 5 minutes past "
            "every full hour as a cronjob. Details about the execution are logged to the file "
            "<tt>var/log/diskspace.log</tt>. You can always execute this program manually "
            "(add the <tt>-v</tt> option to see details about the actions taken)."
        ),
        elements={
            "max_file_age": DictElement(
                parameter_form=FSAge(
                    custom_validate=[validators.NumberInRange(min_value=1)],  # 1 sec
                    prefill=DefaultValue(31536000.0),  # 1 year
                    title=Title("Delete files older than"),
                    help_text=Help(
                        "The historic events (state changes, downtimes etc.) of your hosts and services "
                        "are stored in the monitoring "
                        "history as plain text log files. One history log file contains the monitoring "
                        "history of a given time period of all hosts and services. The files which are "
                        "older than the configured time will be removed on the next execution of the "
                        "disk space cleanup.<br>"
                        "The historic metrics are stored in files for each host and service "
                        "individually. When a host or service has been removed from the monitoring, its "
                        "metric files remain untouched on your disk until the files last update "
                        "(modification time) is longer ago than the configured age."
                    ),
                ),
            ),
            "min_free_bytes": DictElement(
                parameter_form=FSTuple(
                    elements=[
                        DataSize(
                            title=Title("Clean up when disk space is below"),
                            displayed_magnitudes=FILESIZE_MAGNITUDES,
                            custom_validate=[validators.NumberInRange(min_value=1)],  # min 1 byte
                        ),
                        FSAge(
                            title=Title("Never remove files newer than"),
                            custom_validate=[
                                validators.NumberInRange(min_value=1)
                            ],  # minimum 1 sec
                            prefill=DefaultValue(2592000.0),  # 1 month
                            help_text=Help(
                                "With this option you can prevent cleanup of files which have been updated "
                                "within this time range."
                            ),
                        ),
                    ],
                    title=Title("Delete additional files when disk space is below"),
                    help_text=Help(
                        "When the disk space cleanup by file age was not able to gain enough "
                        "free disk space, then the cleanup mechanism starts cleaning up additional "
                        "files. The files are deleted by age, the oldest first, until the files are "
                        "newer than the configured minimum file age."
                    ),
                ),
            ),
            "cleanup_abandoned_host_files": DictElement(
                parameter_form=FSAge(
                    title=Title("Clean up abandoned host files older than"),
                    custom_validate=[validators.NumberInRange(min_value=3600)],  # 1 hour
                    prefill=DefaultValue(2592000.0),  # 1 month
                    help_text=Help(
                        "During monitoring there are several dedicated files created for each host. "
                        "There are, for example, the discovered services, performance data and "
                        "different temporary files created. During deletion of a host, these files "
                        "are normally deleted. But there are cases, where the files are left on "
                        "the disk until manual deletion, for example if you move a host from one "
                        "site to another or deleting a host manually from the configuration.<br>"
                        "The performance data (RRDs) and HW/SW Inventory archive are never deleted "
                        "during host deletion. They are only deleted automatically when you enable "
                        "this option and after the configured period."
                    ),
                ),
            ),
        },
        no_elements_text=Message("Disk space cleanup is disabled"),
    ),
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


class ConfigDomainApache(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @classmethod
    @override
    def ident(cls) -> ConfigDomainName:
        return "apache"

    @override
    def config_dir(self) -> Path:
        return cmk.utils.paths.default_config_dir / "apache.d/wato"

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # see if we can / should move something from activate() here
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
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

    def _write_config_file(self) -> None:
        config = self.get_effective_config()

        output = wato_fileheader()

        if config:
            output += "ServerLimit %d\n" % config["apache_process_tuning"]["number_of_processes"]
            output += "MaxClients %d\n" % config["apache_process_tuning"]["number_of_processes"]

        config_file_path = cmk.utils.paths.omd_root / "etc/apache/conf.d/zzz_check_mk.conf"
        store.save_text_to_file(config_file_path, output)

    def get_effective_config(self) -> GlobalSettings:
        return {
            **self.load(site_specific=False),
            **self.load(site_specific=True),
        }

    @override
    def default_globals(self) -> GlobalSettings:
        return {
            "apache_process_tuning": {
                "number_of_processes": self._get_value_from_config("MaxClients", int, 64),
            }
        }

    def _get_value_from_config(
        self, varname: str, conv_func: Callable[[str], T], default_value: T
    ) -> T:
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


ConfigVariableSiteApacheProcessTuning = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainApache,
    ident="apache_process_tuning",
    form_spec=lambda context: Dictionary(
        title=Title("Apache process tuning"),
        elements={
            "number_of_processes": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Number of apache processes"),
                    help_text=Help(
                        "Use this value to tune the maximum number of apache client requests that will be processed simultaneously "
                        "(maximum number of apache server processes allowed to start). In case you have a lot of incoming "
                        "requests in parallel it may be a good idea to increase this value. But do this carefully, more is "
                        "not always better. The apache processes normally need a decent amount of memory and you should "
                        "only configure as many apache processes as your system can handle in high load situations."
                    ),
                    custom_validate=[validators.NumberInRange(min_value=5)],
                    prefill=DefaultValue(5),
                ),
            ),
        },
    ),
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


class ConfigDomainRRDCached(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @classmethod
    @override
    def ident(cls) -> ConfigDomainName:
        return "rrdcached"

    @override
    def config_dir(self) -> Path:
        return cmk.utils.paths.default_config_dir / "rrdcached.d/wato"

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # see if we can / should move something from activate() here
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
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

    def _write_config_file(self) -> None:
        config = self._get_effective_config()

        output = wato_fileheader()
        for key, val in sorted(config.get("rrdcached_tuning", {}).items()):
            output += "%s=%d\n" % (key, val)

        config_file_path = cmk.utils.paths.omd_root / "etc/rrdcached.d/zzz_check_mk.conf"
        store.save_text_to_file(config_file_path, output)

    def _get_effective_config(self) -> GlobalSettings:
        return {
            **self.load(site_specific=False),
            **self.load(site_specific=True),
        }

    @override
    def default_globals(self) -> GlobalSettings:
        return {
            "rrdcached_tuning": {
                "TIMEOUT": self._get_value_from_config("TIMEOUT", int, 3600),
                "RANDOM_DELAY": self._get_value_from_config("RANDOM_DELAY", int, 1800),
                "FLUSH_TIMEOUT": self._get_value_from_config("FLUSH_TIMEOUT", int, 7200),
                "WRITE_THREADS": self._get_value_from_config("WRITE_THREADS", int, 4),
            }
        }

    def _get_value_from_config(
        self, varname: str, conv_func: Callable[[str], T], default_value: T
    ) -> T:
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


ConfigVariableSiteRRDCachedTuning = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainRRDCached,
    ident="rrdcached_tuning",
    form_spec=lambda context: Dictionary(
        title=Title("RRDCached tuning"),
        elements={
            "TIMEOUT": DictElement(
                required=True,
                parameter_form=FSAge(
                    title=Title("Disk flush interval of updated metrics"),
                    help_text=Help(
                        "Updated metrics are written to disk in the configured interval. "
                        "The write operation is only performed for metrics that are being "
                        "updated. Old metrics are not affected by this option."
                    ),
                    custom_validate=[validators.NumberInRange(min_value=0)],
                    prefill=DefaultValue(0.0),
                ),
            ),
            "RANDOM_DELAY": DictElement(
                required=True,
                parameter_form=FSAge(
                    title=Title("Random delay"),
                    help_text=Help(
                        "The rrdcached will delay writing of each metric for a random "
                        "number of seconds in the range [0..delay]. This will avoid too many "
                        "writes being queued simultaneously. This number should not be "
                        'higher than the value specified in "Disk flush interval of '
                        'updated metrics".'
                    ),
                    custom_validate=[validators.NumberInRange(min_value=0)],
                    prefill=DefaultValue(0.0),
                ),
            ),
            "FLUSH_TIMEOUT": DictElement(
                required=True,
                parameter_form=FSAge(
                    title=Title("Disk flush interval of old data"),
                    help_text=Help(
                        "The entire cache is searched in the interval configured here for old "
                        "values which shall be written to disk. This only concerns RRD files to "
                        "which updates have stopped, so setting this to a high value is "
                        "acceptable in most cases."
                    ),
                    custom_validate=[validators.NumberInRange(min_value=0)],
                    prefill=DefaultValue(0.0),
                ),
            ),
            "WRITE_THREADS": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Number of threads used for writing RRD files"),
                    help_text=Help(
                        "Increasing this number will allow rrdcached to have more simultaneous "
                        "I/O requests into the kernel. This may allow the kernel to re-order "
                        "disk writes, resulting in better disk throughput."
                    ),
                    custom_validate=[validators.NumberInRange(min_value=1, max_value=100)],
                    prefill=DefaultValue(1),
                ),
            ),
        },
    ),
)
