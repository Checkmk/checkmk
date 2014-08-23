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

# Import modules that contain the page functions

import config
import main
import logwatch
import views
import prediction
import sidebar
import actions
import weblib
import dashboard
import login
import help
import bi
import userdb
import notify
import webapi

# map URLs to page rendering functions

pagehandlers.update({
   "index"                    : main.page_index,
   "login"                    : login.page_login,
   "logout"                   : login.page_logout,
   "ajax_switch_help"         : help.ajax_switch_help,
   "switch_site"              : main.ajax_switch_site,
   "edit_views"               : views.page_edit_views,
   "create_view"              : views.page_create_view,
   "create_view_ds"           : views.page_create_view_ds,
   "edit_view"                : views.page_edit_view,
   "count_context_button"     : views.ajax_count_button,
   "export_views"             : views.ajax_export,
   "ajax_set_viewoption"      : views.ajax_set_viewoption,
   "ajax_set_rowselection"    : weblib.ajax_set_rowselection,
   "view"                     : views.page_view,
   "prediction_graph"         : prediction.page_graph,
   "logwatch"                 : logwatch.page_show,
   "side"                     : sidebar.page_side,
   "sidebar_add_snapin"       : sidebar.page_add_snapin,
   "sidebar_snapin"           : sidebar.ajax_snapin,
   "sidebar_fold"             : sidebar.ajax_fold,
   "sidebar_openclose"        : sidebar.ajax_openclose,
   "sidebar_move_snapin"      : sidebar.move_snapin,
   "sidebar_ajax_speedometer" : sidebar.ajax_speedometer,
   "sidebar_ajax_tag_tree"    : sidebar.ajax_tag_tree,
   "sidebar_ajax_tag_tree_enter": sidebar.ajax_tag_tree_enter,
   "sidebar_get_messages"     : sidebar.ajax_get_messages,
   "sidebar_message_read"     : sidebar.ajax_message_read,
   "ajax_search"              : sidebar.ajax_search,
   "search_open"              : sidebar.search_open,
   "switch_master_state"      : sidebar.ajax_switch_masterstate,
   "add_bookmark"             : sidebar.ajax_add_bookmark,
   "del_bookmark"             : sidebar.ajax_del_bookmark,
   "tree_openclose"           : weblib.ajax_tree_openclose,
   "edit_bookmark"            : sidebar.page_edit_bookmark,
   "nagios_action"            : actions.ajax_action,

   "dashboard"                : dashboard.page_dashboard,
   "dashboard_dashlet"        : dashboard.ajax_dashlet,
   "edit_dashboards"          : dashboard.page_edit_dashboards,
   "create_dashboard"         : dashboard.page_create_dashboard,
   "edit_dashboard"           : dashboard.page_edit_dashboard,
   "edit_dashlet"             : dashboard.page_edit_dashlet,
   "delete_dashlet"           : dashboard.page_delete_dashlet,
   "create_view_dashlet"      : dashboard.page_create_view_dashlet,
   "create_view_dashlet_ds"   : dashboard.page_create_view_dashlet_ds,
   "ajax_dashlet_pos"         : dashboard.ajax_dashlet_pos,
   "ajax_popup_add_dashlet"   : dashboard.ajax_popup_add_dashlet,
   "ajax_add_dashlet"         : dashboard.ajax_add_dashlet,

   "ajax_userdb_sync"         : userdb.ajax_sync,
   "notify"                   : notify.page_notify,
   "ajax_inv_render_tree"     : views.ajax_inv_render_tree,

   "webapi"                   : webapi.page_api,
})

