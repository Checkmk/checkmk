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

import log
from log import logger
import cmk.paths

group = _('Site Management')

#.
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

register_configvar(group,
    "AUTOSTART",
    Checkbox(
        title = _("Start during system boot"),
        help = _("Whether or not this site should be started during startup of "
                 "the Check_MK server."),
    ),
    domain = ConfigDomainOMD,
)


def _monitoring_core_choices():
    cores = []
    if not cmk.is_raw_edition():
        cores.append(("cmc", _("Check_MK Micro Core")))

    cores += [
        ("nagios", _("Nagios 3")),
        ("none",   _("No monitoring core")),
    ]

    return cores


register_configvar(group,
    "CORE",
    DropdownChoice(
        title = _("Monitoring core"),
        help = _("Choose the monitoring core to run for monitoring. You can also "
                 "decide to run no monitoring core in this site. This can be useful "
                 "for instances running only a GUI for connecting to other monitoring "
                 "sites."),
        choices = _monitoring_core_choices,
    ),
    domain = ConfigDomainOMD,
)


register_configvar(group,
    "LIVESTATUS_TCP",
    Optional(
        Dictionary(
            elements = [
                ("port", Integer(
                    title = _("TCP port"),
                    minvalue = 1,
                    maxvalue = 65535,
                    default_value = 6557,
                )),
                ("only_from", ListOfStrings(
                    title = _("Restrict access to IP addresses"),
                    help = _("The access to Livestatus via TCP will only be allowed from the "
                             "configured source IP addresses. You can either configure specific "
                             "IP addresses or networks in the syntax <tt>10.3.3.0/24</tt>."),

                    valuespec = IPv4Network(),
                    orientation = "horizontal",
                    allow_empty = False,
                )),
            ],
            optional_keys = [ "only_from" ],
        ),
        title = _("Access to Livestatus via TCP"),
        help = _("Check_MK Livestatus usually listens only on a local UNIX socket - "
                 "for reasons of performance and security. This option is used "
                 "to make it reachable via TCP on a port configurable with LIVESTATUS_TCP_PORT."),
        label = _("Enable Livestatus access via network (TCP)"),
        none_label = _("Livestatus is available locally"),
    ),
    domain = ConfigDomainOMD,
)


register_configvar(group,
    "MKEVENTD",
    Optional(
        ListChoice(
            choices = [
                ("SNMPTRAP",   _("Receive SNMP traps (UDP/162)")),
                ("SYSLOG",     _("Receive Syslog messages (UDP/514)")),
                ("SYSLOG_TCP", _("Receive Syslog messages (TCP/514)")),
            ],
            title = _("Listen for incoming messages via"),
            empty_text = _("Locally enabled"),
        ),
        title = _("Event Console"),
        help = _("This option enables the Event Console - The event processing and "
                 "classification daemon of Check_MK. You can also configure whether "
                 "or not the Event Console shal listen for incoming SNMP traps or "
                 "syslog messages. Please note that only a single Check_MK site per "
                 "Check_MK server can listen for such messages."),
        label = _("Event Console enabled"),
        none_label = _("Event Console disabled"),
        indent = False,
    ),
    domain = ConfigDomainOMD,
)


register_configvar(group,
    "NSCA",
    Optional(
        Integer(
            title = _("Port number"),
            minvalue = 1,
            maxvalue = 65535,
            default_value = 5667,
        ),
        title = _("Listen for passive checks via NSCA"),
        help = _("Enable listening for passible checks via NSCA. With the default configuration "
                 "the TCP port 5667 will be opened. You may also want to update the NSCA "
                 "configuration file %s to fit your needs.") % site_neutral_path("etc/nsca/nsca.cfg"),
        label = _("Enable listening for passive checks using NSCA"),
        none_label = _("NSCA is disabled"),
    ),
    domain = ConfigDomainOMD,
)

#.
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
class ConfigDomainDiskspace(watolib.ConfigDomain):
    needs_sync       = True
    needs_activation = False
    ident            = "diskspace"
    diskspace_config = cmk.paths.omd_root + '/etc/diskspace.conf'

    def activate(self):
        pass


    def load(self, site_specific=False):
        cleanup_settings = {}
        execfile(self.diskspace_config, {}, cleanup_settings)

        if not cleanup_settings:
            return {}

        # Convert old config (min_free_bytes and min_file_age) were independent options
        if "min_free_bytes" in cleanup_settings:
            cleanup_settings["min_free_bytes"] = (cleanup_settings["min_free_bytes"],
                                                  cleanup_settings.pop("min_file_age", 2592000)) # 1 month

        if cleanup_settings.get("cleanup_abandoned_host_files", False) == None:
            del cleanup_settings["cleanup_abandoned_host_files"]

        if cleanup_settings.get("max_file_age", False) == None:
            del cleanup_settings["max_file_age"]

        return {
            "diskspace_cleanup": cleanup_settings,
        }


    def save(self, settings, site_specific=False):
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
            output += '%s = %r\n' % (k, v)

        cmk.store.save_file(self.diskspace_config, output)


    def save_site_globals(self, settings):
        pass


    def default_globals(self):
        diskspace_context = {}
        execfile("%s/bin/diskspace" % cmk.paths.omd_root, {}, diskspace_context)
        return {
            "diskspace_cleanup": diskspace_context["default_config"],
        }



register_configvar(group,
    "diskspace_cleanup",
    Dictionary(
        title = _("Automatic disk space cleanup"),
        help = _("You can configure your monitoring site to free disk space based on the ages "
                 "of files or free space of the volume the site is placed on.<br>"
                 "The monitoring site is executing the program <tt>diskspace</tt> 5 past "
                 "every full hour as cron job. Details about the execution are logged to the file "
                 "<tt>var/log/diskspace.log</tt>. You can always execut this program manually "
                 "(add the <tt>-v</tt> option to see details about the actions taken)."),
        elements = [
            ("max_file_age", Age(
                minvalue = 1, # 1 sec
                default_value = 31536000, # 1 year
                title = _("Delete files older than"),
                help = _("The historic events (state changes, downtimes etc.) of your hosts and services "
                         "is stored in the monitoring "
                         "history as plain text log files. One history log file contains the monitoring "
                         "history of a given time period of all hosts and services. The files which are "
                         "older than the configured time will be removed on the next execution of the "
                         "disk space cleanup.<br>"
                         "The historic metrics are stored in files for each host and service "
                         "individually. When a host or service is removed from the monitoring, it's "
                         "metric files remain untouched on your disk until the files last update "
                         "(modification time) is longer ago than the configure age."),
            )),
            ("min_free_bytes", Tuple(
                elements = [
                    Filesize(
                        title = _("Cleanup when disk space is below"),
                        minvalue = 1, # min 1 byte
                        default_value = 0,
                    ),
                    Age(
                        title = _("Never remove files newer than"),
                        minvalue = 1, # minimum 1 sec
                        default_value = 2592000, # 1 month
                        help = _("With this option you can prevent cleanup of files which have been updated "
                                 "within this time range."),
                    ),
                ],
                title = _("Delete additional files when disk space is below"),
                help = _("When the disk space cleanup by file age was not able to gain enough "
                         "free disk space, then the cleanup mechanism starts cleaning up additional "
                         "files. The files are deleted by age, the oldest first, until the files are "
                         "newer than the configured minimum file age."),
            )),
            ("cleanup_abandoned_host_files", Age(
                title = _("Cleanup abandoned host files older than"),
                help = _("During monitoring there are several dedicated files created for each host. "
                         "There are, for example, the discovered services, performance data and "
                         "different temporary files created. During deletion of a host, these files "
                         "are normally deleted. But there are cases, where the files are left on "
                         "the disk until manual deletion, for example if you move a host from one "
                         "site to another or deleting a host manually from the configuration.<br>"
                         "The performance data (RRDs) and HW/SW inventory archive are never deleted "
                         "during host deletion. They are only deleted automatically when you enable "
                         "this option and after the configured period."),
                minvalue = 3600, # 1 hour
                default_value = 2592000, # 1 month
            )),
        ],
        default_keys = ["cleanup_abandoned_host_files"],
        empty_text = _("Disk space cleanup is disabled"),
    ),
    domain = ConfigDomainDiskspace,
)


add_replication_paths([
    ("file", "diskspace", ConfigDomainDiskspace.diskspace_config),
])


#.
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

class ConfigDomainApache(watolib.ConfigDomain):
    needs_sync       = True
    needs_activation = True
    ident            = "apache"

    def config_dir(self):
        return cmk.paths.default_config_dir + "/apache.d/wato/"


    def activate(self):
        try:
            self._write_config_file()

            p = subprocess.Popen(["omd", "reload", "apache"], shell=False, stdin=open(os.devnull),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)

            stdout = p.communicate()[0]
            if p.returncode != 0:
                raise Exception(stdout)

            return []
        except Exception, e:
            log_exception()
            return ["Failed to activate apache configuration: %s" % (traceback.format_exc())]


    def _write_config_file(self):
        config = self.get_effective_config()

        output = watolib.wato_fileheader()

        if config:
            output += "ServerLimit %d\n" % config["process_tuning"]["number_of_processes"]
            output += "MaxClients %d\n" % config["process_tuning"]["number_of_processes"]

        config_file_path = os.path.join(cmk.paths.omd_root, "etc/apache/conf.d", "zzz_check_mk.conf")
        store.save_file(config_file_path, output)



    def get_effective_config(self):
        config = self.load(site_specific=False)
        config.update(self.load(site_specific=True))
        return config


    def default_globals(self):
        return {
            "process_tuning": {
                "number_of_processes" : self._get_value_from_config("MaxClients", int, 64),
            }
        }


    def _get_value_from_config(self, varname, conv_func, default_value):
        config_files = [ os.path.join(cmk.paths.omd_root, "etc/apache/apache.conf") ]
        config_files += sorted(glob.glob(os.path.join(cmk.paths.omd_root, "etc/apache/conf.d", "*.conf")))

        value = default_value

        for config_file in config_files:
            if config_file.endswith("zzz_check_mk.conf"):
                continue # Skip the file written by this config domain

            for line in open(config_file):
                if line.lstrip().startswith(varname):
                    raw_value = line.split()[1]
                    value = conv_func(raw_value)

        return value


register_configvar(group,
    "process_tuning",
    Dictionary(
        title = _("Apache process tuning"),
        elements = [
            ("number_of_processes", Integer(
                title = _("Number of apache processes"),
                help = _("Use this value to tune the maximum number of apache client requests that will be processed simultaneously "
                         "(maximum number of apache server processes allowed to start). In case you have a lot of incoming "
                         "requests in parallel it may be a good idea to increase this value. But do this carefully, more is "
                         "not always better. The apache processes normally need a decent amount of memory and you should "
                         "only configure as many apache processes as your system can handle in high load situations."),
                minvalue = 5,
            )),
        ],
    ),
    domain = ConfigDomainApache,
)


#.
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

class ConfigDomainRRDCached(watolib.ConfigDomain):
    needs_sync       = True
    needs_activation = True
    ident            = "rrdcached"

    def config_dir(self):
        return cmk.paths.default_config_dir + "/rrdcached.d/wato/"


    def activate(self):
        try:
            self._write_config_file()

            p = subprocess.Popen(["omd", "restart", "rrdcached"], shell=False, stdin=open(os.devnull),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)

            stdout = p.communicate()[0]
            if p.returncode != 0:
                raise Exception(stdout)

            return []
        except Exception, e:
            log_exception()
            return ["Failed to activate rrdcached configuration: %s" % (traceback.format_exc())]


    def _write_config_file(self):
        config = self._get_effective_config()

        output = watolib.wato_fileheader()
        for key, val in sorted(config.get("tuning", {}).items()):
            output += "%s=%d\n" % (key, val)

        config_file_path = os.path.join(cmk.paths.omd_root, "etc/rrdcached.d", "zzz_check_mk.conf")
        store.save_file(config_file_path, output)


    def _get_effective_config(self):
        config = self.load(site_specific=False)
        config.update(self.load(site_specific=True))
        return config


    def default_globals(self):
        return {
            "tuning": {
                "TIMEOUT"       : self._get_value_from_config("TIMEOUT", int, 3600),
                "RANDOM_DELAY"  : self._get_value_from_config("RANDOM_DELAY", int, 1800),
                "FLUSH_TIMEOUT" : self._get_value_from_config("FLUSH_TIMEOUT", int, 7200),
            }
        }


    def _get_value_from_config(self, varname, conv_func, default_value):
        config_files = [ os.path.join(cmk.paths.omd_root, "etc/rrdcached.conf") ]
        config_files += sorted(glob.glob(os.path.join(cmk.paths.omd_root, "etc/rrdcached.d", "*.conf")))

        value = default_value

        for config_file in config_files:
            if config_file.endswith("zzz_check_mk.conf"):
                continue # Skip the file written by this config domain

            for line in open(config_file):
                if line.lstrip().startswith(varname):
                    raw_value = line.split("=")[1]
                    value = conv_func(raw_value)

        return value


register_configvar(group,
    "tuning",
    Dictionary(
        title = _("RRDCached tuning"),
        elements = [
            ("TIMEOUT", Age(
                title = _("Disk flush interval of updated metrics"),
                help = _("Updated metrics are written to disk in the configured interval. "
                         "The write operation is only performed for metrics that are being "
                         "updated. Old metrics are not affected by this option."),
                minvalue = 0,
            )),
            ("RANDOM_DELAY", Age(
                title = _("Random delay"),
                help = _("The rrdcached will delay writing of each metric for a random "
                         "number of seconds in the range [0..delay]. This will avoid too many "
                         "writes being queued simultaneously. This number should not be "
                         "higher than the value specified in \"Disk flush interval of "
                         "updated metrics\"."),
                minvalue = 0,
            )),
            ("FLUSH_TIMEOUT", Age(
                title = _("Disk flush interval of old data"),
                help = _("The entire cache is searched in the interval configured here for old "
                         "values which shal be written to disk. This only concerns RRD files to "
                         "which updates have stopped, so setting this to a high value is "
                         "acceptable in most cases."),
                minvalue = 0,
            )),
        ],
        optional_keys = [],
    ),
    domain = ConfigDomainRRDCached,
)
