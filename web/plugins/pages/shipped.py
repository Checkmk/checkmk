#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

# Import modules that contain the page functions

import main
import page_logwatch
import views
import sidebar
import permissions
import actions
import weblib
import dashboard

# map URLs to page rendering functions

pagehandlers.update({
   "index"                 : main.page_index,
   "main"                  : main.page_main,
   "switch_site"           : main.ajax_switch_site,
   "edit_views"            : views.page_edit_views,
   "edit_view"             : views.page_edit_view,
   "get_edit_column"       : views.ajax_get_edit_column,
   "export_views"          : views.ajax_export,
   "view"                  : views.page_view,
   "logwatch"              : page_logwatch.page,
   "side"                  : sidebar.page_side,
   "sidebar_add_snapin"    : sidebar.page_add_snapin,
   "sidebar_snapin"        : sidebar.ajax_snapin,
   "sidebar_openclose"     : sidebar.ajax_openclose,
   "sidebar_move_snapin"   : sidebar.move_snapin,
   "switch_master_state"   : sidebar.ajax_switch_masterstate,
   "add_bookmark"          : sidebar.ajax_add_bookmark,
   "del_bookmark"          : sidebar.ajax_del_bookmark,
   "tree_openclose"        : weblib.ajax_tree_openclose,
   "edit_bookmark"         : sidebar.page_edit_bookmark,
   "view_permissions"      : permissions.page_view_permissions,
   "edit_permissions"      : permissions.page_edit_permissions,
   "nagios_action"         : actions.ajax_action,
   "dashboard"             : dashboard.page_dashboard,
   "dashboard_resize"      : dashboard.ajax_resize,
   "dashlet_overview"      : dashboard.dashlet_overview,
   "dashlet_hoststats"     : dashboard.dashlet_hoststats,
   "dashlet_servicestats"  : dashboard.dashlet_servicestats,
})

