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

import cmk.paths


# TODO: Diskspace cleanup does not support site specific globals!
class ConfigDomainDiskspace(ConfigDomain):
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



group = _('Site Management')

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


replication_paths.append(("file", "diskspace", ConfigDomainDiskspace.diskspace_config))
