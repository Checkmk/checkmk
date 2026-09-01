#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""File categories and the sensitivity classification of site files"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import auto, Enum, IntEnum
from pathlib import Path
from typing import Literal, NamedTuple

from cmk.diagnostics.internal import Topic

OSWalk = list[tuple[str, list[str], list[str]]]
CheckmkFilesMap = dict[str, Path]


def topic_id(t: Topic) -> str:
    return "topic_" + re.sub(r"[^a-zA-Z0-9_]", "_", t.localize(str))


@dataclass(frozen=True, kw_only=True)
class FileMapConfig:
    file_type: Literal["config", "log"]
    rel_base_folder: Path
    """Base folder of this category's files, relative to the site's root"""
    keep: Callable[[Path], bool]

    def map_generator(
        self,
        base_folder: Path,
        walker: Callable[[Path], OSWalk],
    ) -> CheckmkFilesMap:
        files_map = CheckmkFilesMap()
        for root, _dirs, files in walker(base_folder):
            for file_name in files:
                filepath = Path(root) / file_name
                if self.keep(filepath):
                    rel_filepath = str(filepath.relative_to(base_folder))
                    files_map.setdefault(rel_filepath, filepath)
        return files_map


FILE_MAP_CONFIG = FileMapConfig(
    file_type="config",
    rel_base_folder=Path("etc/check_mk"),
    keep=lambda path: (
        path.name != "ca-certificates.mk"
        and (path.suffix in (".mk", ".conf", ".bi") or path.name == ".wato")
    ),
)

# A log file, optionally rotated (".1") and compressed (".2.gz") by logrotate. Without
# the compressed rotations, a logrotate configuration using "compress" would contribute
# its most recent file only.
_LOG_NAME = re.compile(r"(?:.*\.(?:log|state)|access_log|error_log|stats)(?:\.[0-9]+)?(?:\.gz)?")

FILE_MAP_LOG = FileMapConfig(
    file_type="log",
    rel_base_folder=Path("var/log"),
    keep=lambda path: _LOG_NAME.fullmatch(path.name) is not None,
)


# Component tags of the classification table. The names match the component
# option names of the legacy diagnostics GUI that introduced them.
OPT_COMP_BUSINESS_INTELLIGENCE = "business-intelligence"
OPT_COMP_CMC = "cmc"
OPT_COMP_GLOBAL_SETTINGS = "global-settings"
OPT_COMP_HOSTS_AND_FOLDERS = "hosts-and-folders"
OPT_COMP_LICENSING = "licensing"
OPT_COMP_NOTIFICATIONS = "notifications"


class CheckmkFileEncryption(Enum):
    none = auto()
    rot47 = auto()


class CheckmkFileSensitivity(IntEnum):
    high_sensitive = auto()
    sensitive = auto()
    insensitive = auto()
    unknown = auto()


class CheckmkFileInfo(NamedTuple):
    components: list[str]
    sensitivity: CheckmkFileSensitivity
    description: str
    encryption: CheckmkFileEncryption


def get_checkmk_file_info(rel_filepath: str, component: str | None = None) -> CheckmkFileInfo:
    # Some files like hosts.mk or rules.mk may be located in folder hierarchies.
    # Thus we have to find them via name. The presedence is as following:
    # 1. CheckmkFileInfoByNameMap
    # 2. CheckmkFileInfoByRelFilePathMap
    #
    # Note:
    # A combination FILE + COMPONENT may be only in ONE of these two maps. Otherwise
    # a component collects too many files.
    # Example:
    # - 'Global settings' collects
    #       all 'global.mk'
    #   => ONE entry in CheckmkFileInfoByNameMap
    #
    # - 'Notifications' collects
    #       conf.d/wato/global.mk
    #       mknotify.d/wato/global.mk
    #       multisite.d/wato/global.mk
    #   => MULTIPLE entries in CheckmkFileInfoByRelFilePathMap
    #      (Otherwise all other 'global.mk' would be associated with 'Notifications')

    # update.log.2.gz -> update.log
    rel_filepath = re.sub(r"\.[0-9]+(\.gz)?", "", rel_filepath)

    file_info_by_rel_filepath = CheckmkFileInfoByRelFilePathMap.get(rel_filepath)
    if file_info_by_rel_filepath is not None and (
        component is None or component in file_info_by_rel_filepath.components
    ):
        return file_info_by_rel_filepath

    file_info_by_name = CheckmkFileInfoByNameMap.get(Path(rel_filepath).name)
    if file_info_by_name is not None and (
        component is None or component in file_info_by_name.components
    ):
        return file_info_by_name

    return CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.unknown,
        description="",
        encryption=CheckmkFileEncryption.none,
    )


# Feel free to extend the maps:
# - config file entries are relative to "etc/check_mk".
# - log file entries are relative to "var/log".
CheckmkFileInfoByNameMap: dict[str, CheckmkFileInfo] = {
    # config files
    "global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_GLOBAL_SETTINGS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Global settings for a particular component.",
        encryption=CheckmkFileEncryption.none,
    ),
    "hosts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all hosts of a particular folder, including their attributes.",
        encryption=CheckmkFileEncryption.none,
    ),
    "rules.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all rules assigned to a particular folder.",
        encryption=CheckmkFileEncryption.none,
    ),
    "sites.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_GLOBAL_SETTINGS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        encryption=CheckmkFileEncryption.none,
        description="Configuration for the distributed monitoring.",
    ),
    "sitespecific.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        encryption=CheckmkFileEncryption.none,
        description="Sitespecific global settings for a particular component.",
    ),
    "tags.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains tag groups and auxiliary tags.",
        encryption=CheckmkFileEncryption.none,
    ),
    ".wato": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_HOSTS_AND_FOLDERS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the folder properties of a particular folder.",
        encryption=CheckmkFileEncryption.none,
    ),
}

CheckmkFileInfoByRelFilePathMap: dict[str, CheckmkFileInfo] = {
    # config files
    "apache.conf": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Basic Apache configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "backup.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Backup configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "backup_keys.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Backup encryption keys.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/distributed_wato.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the information about if the site is a remotesite.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/microcore.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Basic Microcore configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/mkeventd.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Basic Eventconsole configuration for the core.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/pnp4nagios.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Basic PNP4Nagios configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/alert_handlers.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Alert handler configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/contacts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains users and their properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the global settings of a site.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the contact groups.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/influxdb_connections.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the InfluxDB configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/notifications.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the notification rules.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/notification_parameter.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the configuration rules of the notification methods.",
        encryption=CheckmkFileEncryption.none,
    ),
    "dcd.d/wato/distributed.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the information if DCD is used on this site.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing.d/notification_settings.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains set of users to be notified on licensing situations.",
        encryption=CheckmkFileEncryption.none,
    ),
    "liveproxyd.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Basic Liveproxy configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "main.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="The main config file, which is used if you don't use the Setup features of the GUI.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mkeventd.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Basic Eventconsole configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mkeventd.d/wato/global.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the configuration of the Event Console.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mknotifyd.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the notification spooler's global settings.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Basic UI configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/licensing_settings.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains licensing related settings for mode of connection, e.g. online verification, credentials, etc.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/liveproxyd.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Liveproxy configuration for the UI",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/mkeventd.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Eventconsole configuration for the UI",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/sites.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Distributed monitoring configuration.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/agent_registration.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the Agent registration rules.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/agent_signature_keys.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the Bakery's Agent signature keys.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/bi_config.bi": CheckmkFileInfo(
        components=[
            OPT_COMP_BUSINESS_INTELLIGENCE,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the Business Intelligence rules and aggregations.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/customers.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the customers definition in an MSP environment.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains GUI related global settings.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains GUI related contact group properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/sites.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the configuration of the distributed monitoring.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/users.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains GUI related user properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/user_connections.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains GUI related user properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    "otel_collector.d/otel_collector_prom_scrape.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Configuration of the Open Telemetry Prometheus scraper.",
        encryption=CheckmkFileEncryption.none,
    ),
    "otel_collector.d/otel_collector_receivers.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Configuration of the Open Telemetry receiver.",
        encryption=CheckmkFileEncryption.none,
    ),
    # Log files
    "agent-receiver/access.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The access log of the agent receiver.",
        encryption=CheckmkFileEncryption.none,
    ),
    "agent-receiver/agent-receiver.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The operational log of the agent receiver.",
        encryption=CheckmkFileEncryption.none,
    ),
    "agent-receiver/error.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The error log of the agent receiver.",
        encryption=CheckmkFileEncryption.none,
    ),
    "agent-registration.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log for the TLS registration of the agents.",
        encryption=CheckmkFileEncryption.none,
    ),
    "alerts.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Log file with all events relevant to the alert handler (logged by the alert helper).",
        encryption=CheckmkFileEncryption.none,
    ),
    "apache/access_log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Contains all requests that are sent to the site's apache server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "apache/error_log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="this log file contains all errors that occur when requests are sent to the site's apache server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "apache/stats": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="this log file contains current access statistics about the site's apache server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "automatic-host-removal.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains events from the Automatic host removal feature.",
        encryption=CheckmkFileEncryption.none,
    ),
    "automation-helper/access.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all requests that are sent to the automation helper server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "automation-helper/automation-helper.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all activity inside the automation helper application.",
        encryption=CheckmkFileEncryption.none,
    ),
    "automation-helper/error.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all errors that occur when requests are sent to the automation helper server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "cmc.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="In this file messages from starting and stopping the CMC can be found, as well as general warnings and error messages related to the core and the check helpers.",
        encryption=CheckmkFileEncryption.none,
    ),
    "dcd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file for the Dynamic Configuration Daemon (DCD).",
        encryption=CheckmkFileEncryption.none,
    ),
    "diskspace.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="The log file of the automatic disk space cleanup.",
        encryption=CheckmkFileEncryption.none,
    ),
    "jaeger.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the tracing component jaeger.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing.log": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Logs everything related to the licensing.",
        encryption=CheckmkFileEncryption.none,
    ),
    "liveproxyd.log": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Log file for the Livestatus proxies.",
        encryption=CheckmkFileEncryption.none,
    ),
    "liveproxyd.state": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The current state of the Livestatus proxies in a readable form. This file is updated every 5 seconds.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mknotifyd.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The notification spooler’s log file.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mkeventd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The event console log file. This will show you the processing of the incoming messages, matching of the rule packs and the processing of the matched mibs.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mknotifyd.state": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The current status of the notification spooler. This is primarily relevant for notifications in distributed environments.",
        encryption=CheckmkFileEncryption.none,
    ),
    "notify.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The notification module’s log file. This will show you the rule based processing of the notifications.",
        encryption=CheckmkFileEncryption.none,
    ),
    "otel-collector.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the Open Telemetry daemon.",
        encryption=CheckmkFileEncryption.none,
    ),
    "rrdcached.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the rrd cache daemon.",
        encryption=CheckmkFileEncryption.none,
    ),
    "redis-server.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the redis-server of the Checkmk site.",
        encryption=CheckmkFileEncryption.none,
    ),
    "security.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="All modules forward security relevant events to this log file.",
        encryption=CheckmkFileEncryption.none,
    ),
    "stunnel-server.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Log file of the stunnel, which handles encrypted communication between sites.",
        encryption=CheckmkFileEncryption.none,
    ),
    "product_usage_analytics.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="This log files contains all activity and errors of the product usage analytics module.",
        encryption=CheckmkFileEncryption.none,
    ),
    "ui-job-scheduler/access.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all requests that are sent to the ui-job-scheduler server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "ui-job-scheduler/ui-job-scheduler.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all activity inside the ui-job-scheduler application.",
        encryption=CheckmkFileEncryption.none,
    ),
    "ui-job-scheduler/error.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains all errors that occur when requests are sent to the ui-job-scheduler server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "update.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the output of the omd update calls.",
        encryption=CheckmkFileEncryption.none,
    ),
    "web.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the checkmk weg gui. Here you can find all kind of automations call, ldap sync and some failing GUI extensions.",
        encryption=CheckmkFileEncryption.none,
    ),
    "xinetd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log of the Internet superserver xinetd which handles connections to the livestatus port.",
        encryption=CheckmkFileEncryption.none,
    ),
}
