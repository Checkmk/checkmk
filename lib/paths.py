#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

"""This module serves the path structure of the Check_MK environment
to all components of Check_MK."""

import os

from .exceptions import MKGeneralException

# TODO: Clean this up one day by using the way recommended by gettext.
# (See https://docs.python.org/2/library/gettext.html). For this we
# need the path to the locale files here.
try:
    _
except NameError:
    _ = lambda x: x # Fake i18n when not available


#
# First declare the possible paths for the linters. Then set it within _set_paths()
#

# TODO: Add piggyback_dir and use it in code
omd_root                  = None
default_config_dir        = None
main_config_file          = None
final_config_file         = None
local_config_file         = None
check_mk_config_dir       = None
modules_dir               = None
var_dir                   = None
log_dir                   = None
autochecks_dir            = None
precompiled_hostchecks_dir= None
snmpwalks_dir             = None
counters_dir              = None
tcp_cache_dir             = None
snmp_cache_dir            = None
snmp_scan_cache_dir       = None
tmp_dir                   = None
logwatch_dir              = None
nagios_objects_file       = None
nagios_command_pipe_path  = None
check_result_path         = None
nagios_status_file        = None
nagios_conf_dir           = None
nagios_config_file        = None
nagios_startscript        = None
nagios_binary             = None
apache_config_dir         = None
htpasswd_file             = None
livestatus_unix_socket    = None
pnp_rraconf_dir           = None
livebackendsdir           = None

share_dir                 = None
checks_dir                = None
notifications_dir         = None
inventory_dir             = None
check_manpages_dir        = None
agents_dir                = None
mibs_dir                  = None
web_dir                   = None
pnp_templates_dir         = None
doc_dir                   = None
locale_dir                = None
bin_dir                   = None
lib_dir                   = None
mib_dir                   = None

# TODO: Add active_checks_dir and make it used in code
local_share_dir           = None
local_checks_dir          = None
local_notifications_dir   = None
local_inventory_dir       = None
local_check_manpages_dir  = None
local_agents_dir          = None
local_mibs_dir            = None
local_web_dir             = None
local_pnp_templates_dir   = None
local_doc_dir             = None
local_locale_dir          = None
local_bin_dir             = None
local_lib_dir             = None
local_mib_dir             = None


def _set_paths():
    omd_root = _omd_root()

    globals().update({
        "omd_root"                    : omd_root,
        "default_config_dir"          : os.path.join(omd_root, "etc/check_mk"),
        "main_config_file"            : os.path.join(omd_root, "etc/check_mk/main.mk"),
        "final_config_file"           : os.path.join(omd_root, "etc/check_mk/final.mk"),
        "local_config_file"           : os.path.join(omd_root, "etc/check_mk/local.mk"),
        "check_mk_config_dir"         : os.path.join(omd_root, "etc/check_mk/conf.d"),
        "modules_dir"                 : os.path.join(omd_root, "share/check_mk/modules"),
        "var_dir"                     : os.path.join(omd_root, "var/check_mk"),
        "log_dir"                     : os.path.join(omd_root, "var/log"),
        "autochecks_dir"              : os.path.join(omd_root, "var/check_mk/autochecks"),
        "precompiled_hostchecks_dir"  : os.path.join(omd_root, "var/check_mk/precompiled"),
        "snmpwalks_dir"               : os.path.join(omd_root, "var/check_mk/snmpwalks"),
        "counters_dir"                : os.path.join(omd_root, "tmp/check_mk/counters"),
        "tcp_cache_dir"               : os.path.join(omd_root, "tmp/check_mk/cache"),
        "snmp_cache_dir"              : os.path.join(omd_root, "tmp/check_mk/snmp_cache"),
        "snmp_scan_cache_dir"         : os.path.join(omd_root, "tmp/check_mk/snmp_scan_cache"),
        "tmp_dir"                     : os.path.join(omd_root, "tmp/check_mk"),
        "logwatch_dir"                : os.path.join(omd_root, "var/check_mk/logwatch"),
        "nagios_startscript"          : os.path.join(omd_root, "etc/init.d/core"),

        # Switched via symlinks on icinga/nagios change
        "nagios_conf_dir"             : os.path.join(omd_root, "etc/nagios/conf.d"),
        "nagios_objects_file"         : os.path.join(omd_root, "etc/nagios/conf.d/check_mk_objects.cfg"),
        "check_result_path"           : os.path.join(omd_root, "tmp/nagios/checkresults"),
        "nagios_status_file"          : os.path.join(omd_root, "tmp/nagios/status.dat"),

        "apache_config_dir"           : os.path.join(omd_root, "etc/apache"),
        "htpasswd_file"               : os.path.join(omd_root, "etc/htpasswd"),
        "livestatus_unix_socket"      : os.path.join(omd_root, "tmp/run/live"),
        "pnp_rraconf_dir"             : os.path.join(omd_root, "share/check_mk/pnp-rraconf"),
        "livebackendsdir"             : os.path.join(omd_root, "share/check_mk/livestatus"),
    })

    _set_core_specific_paths()
    _set_overridable_paths()
    _set_overridable_paths(local=True)


def _omd_root():
    return os.environ.get("OMD_ROOT", "")
    #try:
    #except KeyError:
    #    raise MKGeneralException(_("OMD_ROOT environment variable not set. You can "
    #                               "only execute this in an OMD site."))


def _set_core_specific_paths():
    omd_root = _omd_root()
    core = _get_core_name()

    if core == "icinga":
        globals().update({
            "nagios_binary"               : os.path.join(omd_root, "bin/icinga"),
            "nagios_config_file"          : os.path.join(omd_root, "tmp/icinga/icinga.cfg"),
            "nagios_command_pipe_path"    : os.path.join(omd_root, "tmp/run/icinga.cmd"),
        })
    else:
        globals().update({
            "nagios_binary"               : os.path.join(omd_root, "bin/nagios"),
            "nagios_config_file"          : os.path.join(omd_root, "tmp/nagios/nagios.cfg"),
            "nagios_command_pipe_path"    : os.path.join(omd_root, "tmp/run/nagios.cmd"),
        })


# TODO: Find a better way to determine the currently configured core.
# For example generalize the etc/check_mk/conf.d/microcore.mk which is written by the CORE
# hook -> Change the name to core.mk and write it for all configured cores.
def _get_core_name():
    try:
        for l in open(os.path.join(omd_root, "etc/omd/site.conf")):
            if l.startswith("CONFIG_CORE='"):
                return l.split("'")[1]
    except IOError, e:
        # At least in test environment the file is not available. We only added this try/except for
        # this case. This should better be solved in a cleaner way.
        if e.errno == 2:
            pass
        else:
            raise


def _set_overridable_paths(local=False):
    rel_base   = "local" if local else ""
    var_prefix = "local_" if local else ""

    globals().update({
        var_prefix+"share_dir"          : os.path.join(omd_root, rel_base, "share/check_mk"),
        var_prefix+"checks_dir"         : os.path.join(omd_root, rel_base, "share/check_mk/checks"),
        var_prefix+"notifications_dir"  : os.path.join(omd_root, rel_base, "share/check_mk/notifications"),
        var_prefix+"inventory_dir"      : os.path.join(omd_root, rel_base, "share/check_mk/inventory"),
        var_prefix+"check_manpages_dir" : os.path.join(omd_root, rel_base, "share/check_mk/checkman"),
        var_prefix+"agents_dir"         : os.path.join(omd_root, rel_base, "share/check_mk/agents"),
        var_prefix+"mibs_dir"           : os.path.join(omd_root, rel_base, "share/check_mk/mibs"),
        var_prefix+"web_dir"            : os.path.join(omd_root, rel_base, "share/check_mk/web"),
        var_prefix+"pnp_templates_dir"  : os.path.join(omd_root, rel_base, "share/check_mk/pnp-templates"),
        var_prefix+"doc_dir"            : os.path.join(omd_root, rel_base, "share/doc/check_mk"),
        var_prefix+"locale_dir"         : os.path.join(omd_root, rel_base, "share/check_mk/locale"),
        var_prefix+"bin_dir"            : os.path.join(omd_root, rel_base, "bin"),
        var_prefix+"lib_dir"            : os.path.join(omd_root, rel_base, "lib"),
        var_prefix+"mib_dir"            : os.path.join(omd_root, rel_base, "share/snmp/mibs"),
    })


_set_paths()
