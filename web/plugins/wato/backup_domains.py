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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

backup_domains = {}

# Temporary variable which stores settings during the backup process
backup_perfdata_enabled = True
def performancedata_restore(pre_restore = True):
    global backup_perfdata_enabled
    site = default_site()
    html.live.set_only_sites([site])

    if pre_restore:
        data = html.live.query("GET status\nColumns: process_performance_data")
        backup_perfdata_enabled = data[0][0] == 1
        # Return if perfdata is not activated - nothing to do..
        if not backup_perfdata_enabled:
            return []
    elif not backup_perfdata_enabled:
        return []
    command = pre_restore and "DISABLE_PERFORMANCE_DATA" or "ENABLE_PERFORMANCE_DATA"
    html.live.command("[%d] %s" % (int(time.time()), command), site)
    html.live.set_only_sites()
    return []

if not defaults.omd_root:
    backup_domains.update( {
    "noomd-config": {
      "group"       : _("Configuration"),
      "title"       : _("WATO Configuration"),
      "prefix"      : defaults.default_config_dir,
      "paths"       : [
                        ("dir",  "conf.d/wato"),
                        ("dir",  "multisite.d/wato"),
                        ("file", "multisite.d/sites.mk")
                      ],
      "default"     : True,
    },
    "noomd-personalsettings": {
          "title"       : _("Personal User Settings and Custom Views"),
          "prefix"      :  defaults.var_dir,
          "paths"       : [ ("dir", "web") ],
          "default"     : True
    },
    "noomd-authorization": {
      "group"       : _("Configuration"),
      "title"       : _("Local Authentication Data"),
      "prefix"      : os.path.dirname(defaults.htpasswd_file),
      "paths"       : [
                        ("file", "htpasswd"),
                        ("file", "auth.secret"),
                        ("file", "auth.serials")
                      ],
      "cleanup"     : False,
      "default"     : True
    }})
else:
    backup_domains.update({
        "check_mk": {
          "group"       : _("Configuration"),
          "title"       : _("Hosts, Services, Groups, Timeperiods, Business Intelligence and Monitoring Configuration"),
          "prefix"      : defaults.default_config_dir,
          "paths"       : [
                            ("file", "liveproxyd.mk"),
                            ("file", "main.mk"),
                            ("file", "final.mk"),
                            ("file", "local.mk"),
                            ("file", "mkeventd.mk"),

                            ("dir", "conf.d"),
                            ("dir", "multisite.d"),
                            ("dir", "mkeventd.d"),
                            ("dir", "mknotifyd.d"),
                          ],
          "default"     : True,
        },
        "authorization": {
          # This domain is obsolete
          # It no longer shows up in the backup screen
          "deprecated"  : True,
          "group"       : _("Configuration"),
          "title"       : _("Local Authentication Data"),
          "prefix"      : os.path.dirname(defaults.htpasswd_file),
          "paths"       : [
                            ("file", "htpasswd"),
                            ("file", "auth.secret"),
                            ("file", "auth.serials")
                          ],
          "cleanup"     : False,
          "default"     : True,
        },
        "authorization_v1": {
          "group"       : _("Configuration"),
          "title"       : _("Local Authentication Data"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("file", "etc/htpasswd"),
                            ("file", "etc/auth.secret"),
                            ("file", "etc/auth.serials"),
                            ("file", "var/check_mk/web/*/serial.mk")
                          ],
          "cleanup"     : False,
          "default"     : True
        },
        "personalsettings": {
          "title"       : _("Personal User Settings and Custom Views"),
          "prefix"      :  defaults.var_dir,
          "paths"       : [ ("dir", "web") ],
          "exclude"     : [ "*/serial.mk" ],
          "cleanup"     : False,
        },
        "autochecks": {
          "group"       : _("Configuration"),
          "title"       : _("Automatically Detected Services"),
          "prefix"      : defaults.autochecksdir,
          "paths"       : [ ("dir", "") ],
        },
        "snmpwalks": {
          "title"       : _("Stored SNMP Walks"),
          "prefix"      : defaults.snmpwalks_dir,
          "paths"       : [ ("dir", "") ],
        },
        "logwatch": {
          "group"       : _("Historic Data"),
          "title"       : _("Logwatch Data"),
          "prefix"      : defaults.var_dir,
          "paths"       : [
                            ("dir",  "logwatch"),
                          ],
        },
        "corehistory": {
          "group"       : _("Historic Data"),
          "title"       : _("Monitoring History"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/nagios/archive"),
                            ("file", "var/nagios/nagios.log"),
                            ("dir",  "var/icinga/archive"),
                            ("file", "var/icinga/icinga.log"),
                            ("dir",  "var/check_mk/core/archive"),
                            ("file", "var/check_mk/core/history"),
                          ],
        },
        "performancedata": {
          "group"        : _("Historic Data"),
          "title"        : _("Performance Data"),
          "prefix"       : defaults.omd_root,
          "paths"        : [
                             ("dir",  "var/pnp4nagios/perfdata"),
                             ("dir",  "var/rrdcached"),
                           ],
          "pre_restore"  : lambda: performancedata_restore(pre_restore = True),
          "post_restore" : lambda: performancedata_restore(pre_restore = False),
          "checksum"    : False,
        },
        "applicationlogs": {
          "group"       : _("Historic Data"),
          "title"       : _("Application Logs"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/log"),
                            ("file", "var/check_mk/notify/notify.log"),
                            ("file", "var/nagios/livestatus.log"),
                            ("dir",  "var/pnp4nagios/log"),
                          ],
          "checksum"    : False,
        },
        "mkeventstatus": {
          "group"       : _("Configuration"),
          "title"       : _("Event Console Configuration"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "etc/check_mk/mkeventd.d"),
                          ],
          "default"     : True
        },
        "mkeventhistory": {
          "group"       : _("Historic Data"),
          "title"       : _("Event Console Archive and Current State"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/mkeventd/history"),
                            ("file", "var/mkeventd/status"),
                            ("file", "var/mkeventd/messages"),
                            ("dir",  "var/mkeventd/messages-history"),
                          ],
        },
        "dokuwiki": {
          "title"       : _("Doku Wiki Pages and Settings"),
          "prefix"      : defaults.omd_root,
          "paths"       : [
                            ("dir",  "var/dokuwiki"),
                          ],
        },
        "nagvis": {
          "title"       : _("NagVis Maps, Configurations and User Files"),
          "prefix"      : defaults.omd_root,
          "exclude"     : [
                            "etc/nagvis/apache.conf",
                            "etc/nagvis/conf.d/omd.ini.php",
                            "etc/nagvis/conf.d/cookie_auth.ini.php",
                            "etc/nagvis/conf.d/urls.ini.php"
                          ],
          "paths"       : [
                            ("dir",  "local/share/nagvis"),
                            ("dir",  "etc/nagvis"),
                            ("dir",  "var/nagvis"),
                          ],
        },
    })
