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

# Please refer to nagvis_icon.mk to see a way how to add the nagvismaps custom macro

# copy me to ~/local/share/check_mk/web/pluins/icon and restart the site apache

def paint_nagvis_image(what, row, tags, custom_vars):
    if what != 'host' or not custom_vars.get('NAGVISMAPS'):
        return
    h = ""
    for nagvis_map in custom_vars['NAGVISMAPS'].split(','):
        h += '<a href="../nagvis/frontend/nagvis-js/index.php?mod=Map&act=view&show=%s" title="%s"><img class=icon src="images/icon_nagvis.png"/></a>' \
        % ( nagvis_map, nagvis_map )

    return h

multisite_icons.append({
    'paint':           paint_nagvis_image,
})
