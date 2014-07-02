#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# put this script into local/share/check_mk/web/plugins/wato
# of a slave site
# this deletes all WATO folders immediatelly after sync except one
# folder with the same name as the site name of the slave site
#
# it can be used to avoid a customer to see config of other customers
# for this to work you need to have one folder per customer on the top
# level and one site per customer with exactly the same name
def pre_activate_changes_cleanup(_unused):
    log = open('%s/tmp/hook.log' % defaults.omd_root,'w')
    log.write('omd_site: %s, omd_root: %s\n' % (defaults.omd_site, defaults.omd_root))
    confd = "%s/etc/check_mk/conf.d/wato/" % defaults.omd_root
    for dirname, dirnames, filenames in os.walk(confd):
        for subdirname in dirnames:
            if subdirname == defaults.omd_site:
                log.write("keeping subdir: %s\n" % subdirname)
            else:
                log.write("deletinging subdir: %s\n" % subdirname)
                shutil.rmtree(confd + subdirname)
        break
    log.close()

api.register_hook('pre-activate-changes', pre_activate_changes_cleanup)
