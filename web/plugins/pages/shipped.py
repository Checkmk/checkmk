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

# Import modules that contain the page functions

import main
import logwatch
import views
import prediction
import sidebar
import weblib
import dashboard
import login
import help
import bi
import userdb
import notify
import webapi
import visuals
import crash_reporting
import metrics
import werks
import inventory
import notifications
import valuespec


# map URLs to page rendering functions

pagehandlers.update({
    "index"                         : main.page_index,
    "login"                         : login.page_login,
    "logout"                        : login.page_logout,
    "ajax_switch_help"              : help.ajax_switch_help,
    "ajax_vs_autocomplete"          : valuespec.TextAsciiAutocomplete.ajax_handler,
    "edit_views"                    : views.page_edit_views,
    "create_view"                   : views.page_create_view,
    "create_view_infos"             : views.page_create_view_infos,
    "edit_view"                     : views.page_edit_view,
    "count_context_button"          : views.ajax_count_button,
    "export_views"                  : views.ajax_export,
    "ajax_set_viewoption"           : views.ajax_set_viewoption,
    "view"                          : views.page_view,
    "ajax_inv_render_tree"          : views.ajax_inv_render_tree,
    "ajax_reschedule"               : views.ajax_reschedule,
    "host_inv_api"                  : inventory.page_host_inv_api,
    "host_service_graph_popup"      : metrics.page_host_service_graph_popup,
    "graph_dashlet"                 : metrics.page_graph_dashlet,
    "ajax_set_rowselection"         : weblib.ajax_set_rowselection,
    "prediction_graph"              : prediction.page_graph,
    "logwatch"                      : logwatch.page_show,
    "side"                          : sidebar.page_side,
    "sidebar_add_snapin"            : sidebar.page_add_snapin,
    "sidebar_snapin"                : sidebar.ajax_snapin,
    "sidebar_fold"                  : sidebar.ajax_fold,
    "sidebar_openclose"             : sidebar.ajax_openclose,
    "sidebar_move_snapin"           : sidebar.move_snapin,
    "sidebar_ajax_speedometer"      : sidebar.ajax_speedometer,
    "sidebar_ajax_tag_tree"         : sidebar.ajax_tag_tree,
    "sidebar_ajax_tag_tree_enter"   : sidebar.ajax_tag_tree_enter,
    "sidebar_get_messages"          : sidebar.ajax_get_messages,
    "sidebar_message_read"          : sidebar.ajax_message_read,
    "ajax_search"                   : sidebar.ajax_search,
    "search_open"                   : sidebar.search_open,
    "switch_master_state"           : sidebar.ajax_switch_masterstate,
    "switch_site"                   : sidebar.ajax_switch_site,
    "add_bookmark"                  : lambda: sidebar.ajax_add_bookmark(),
    "tree_openclose"                : weblib.ajax_tree_openclose,

    "dashboard"                     : dashboard.page_dashboard,
    "dashboard_dashlet"             : dashboard.ajax_dashlet,
    "edit_dashboards"               : dashboard.page_edit_dashboards,
    "create_dashboard"              : dashboard.page_create_dashboard,
    "edit_dashboard"                : dashboard.page_edit_dashboard,
    "edit_dashlet"                  : dashboard.page_edit_dashlet,
    "delete_dashlet"                : dashboard.page_delete_dashlet,
    "create_view_dashlet"           : dashboard.page_create_view_dashlet,
    "create_view_dashlet_infos"     : dashboard.page_create_view_dashlet_infos,
    "ajax_dashlet_pos"              : dashboard.ajax_dashlet_pos,
    "ajax_delete_user_notification" : lambda: dashboard.ajax_delete_user_notification(),

    "ajax_popup_add_visual"         : visuals.ajax_popup_add,
    "ajax_add_visual"               : visuals.ajax_add_visual,

    "ajax_userdb_sync"              : userdb.ajax_sync,
    "notify"                        : notify.page_notify,

    "ajax_inv_render_tree"          : views.ajax_inv_render_tree,

    "ajax_popup_icon_selector"      : views.ajax_popup_icon_selector,
    "ajax_popup_action_menu"        : views.ajax_popup_action_menu,

    "webapi"                        : webapi.page_api,

    "crashed_check"                 : lambda: crash_reporting.page_crashed("check"),
    "gui_crash"                     : lambda: crash_reporting.page_crashed("gui"),
    "download_crash_report"         : crash_reporting.page_download_crash_report,

    "version"                       : werks.page_version,
    "werk"                          : werks.page_werk,
    "clear_failed_notifications"    : notifications.page_clear,
})
