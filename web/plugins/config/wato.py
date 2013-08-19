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

wato_enabled            = True
wato_host_tags          = []
wato_aux_tags           = []
wato_hide_filenames     = True
wato_hide_hosttags      = False
wato_hide_varnames      = True
wato_hide_help_in_lists = True
wato_max_snapshots      = 50
wato_num_hostspecs      = 12
wato_num_itemspecs      = 15
wato_activation_method  = 'restart'
wato_write_nagvis_auth  = False
wato_use_git            = False
wato_hidden_users       = []
wato_user_attrs         = []

def tag_alias(tag):
    for entry in wato_host_tags:
        id, title, tags = entry[:3]
        for t in tags:
            if t[0] == tag:
                return t[1]
    for id, alias in wato_aux_tags:
        if id == tag:
            return alias

def tag_group_title(tag):
    for entry in wato_host_tags:
        id, title, tags = entry[:3]
        for t in tags:
            if t[0] == tag:
                return title
