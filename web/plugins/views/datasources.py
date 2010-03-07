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


##################################################################################
# Data sources
##################################################################################

multisite_datasources["hosts"] = {
    "title"   : "All hosts",
    "table"   : "hosts",
    "infos"   : [ "host" ],
    "columns" : ["host_name", "host_alias", "host_state", "host_has_been_checked", "host_downtimes",
		 "host_scheduled_downtime_depth", "host_notes_url_expanded", "host_action_url_expanded", 
		 "host_active_checks_enabled", "host_accept_passive_checks", "host_acknowledged", "host_notifications_enabled",
		 "host_comments", "host_is_flapping", "host_is_executing",
		 "host_plugin_output", "host_num_services", "host_num_services_pending", "host_num_services_ok", 
		 "host_num_services_warn", 
                 "host_num_services_unknown", "host_num_services_crit" ],
}

multisite_datasources["hostsbygroup"] = {
    "title"   : "Hosts grouped by host groups",
    "table"   : "hostsbygroup",
    "infos"   : [ "host", "hostgroup" ],
    "columns" : ["hostgroup_name", "hostgroup_alias",
		 "host_scheduled_downtime_depth", "host_notes_url_expanded", "host_action_url_expanded",
		 "host_active_checks_enabled", "host_accept_passive_checks", "host_acknowledged", "host_notifications_enabled",
		 "host_comments", "host_is_flapping", "host_is_executing",
                 "host_name", "host_alias", "host_state", "host_has_been_checked", "host_downtimes", 
		 "host_plugin_output", "host_num_services", "host_num_services_pending", "host_num_services_ok", 
		 "host_num_services_warn", 
                 "host_num_services_unknown", "host_num_services_crit" ],
}
multisite_datasources["services"] = {
    "title"   : "All services",
    "table"   : "services",
    "infos"   : [ "host", "service" ],
    "columns" : [ "service_description", "service_plugin_output", "service_state", "service_has_been_checked", 
		  "service_scheduled_downtime_depth", "service_notes_url_expanded", "service_action_url_expanded", 
		  "service_active_checks_enabled", "service_accept_passive_checks", "service_acknowledged", "service_notifications_enabled",
		  "service_comments", "service_is_flapping", "service_is_executing", "service_check_command",
                  "host_name", "host_state", "host_has_been_checked", "service_last_check",
		  "service_last_state_change", "service_downtimes", "service_perf_data", 
		  "service_max_check_attempts", "service_current_attempt", "service_in_notification_period",
		  "service_scheduled_downtime_depth", "service_is_flapping", "service_contacts",
			  ],
}

multisite_datasources["servicesbygroup"] = {
    "title"   : "Services grouped by service groups",
    "table"   : "servicesbygroup",
    "infos"   : [ "host", "service", "servicegroup" ],
    "columns" : [ "servicegroup_alias", "servicegroup_name", 
		  "service_description", "service_plugin_output", "service_state", "service_has_been_checked", 
		  "service_scheduled_downtime_depth", "service_notes_url_expanded", "service_action_url_expanded", 
		  "service_active_checks_enabled", "service_accept_passive_checks", "service_acknowledged", "service_notifications_enabled",
		  "service_comments", "service_is_flapping", "service_is_executing",
                  "host_name", "host_state", "host_has_been_checked", 
		  "service_last_state_change", "service_downtimes", "service_perf_data",
		      "service_max_check_attempts", "service_current_attempt", "service_in_notification_period",
		  "service_scheduled_downtime_depth", "service_is_flapping", "service_contacts",
		      ],
}
multisite_datasources["servicesbyhostgroup"] = {
    "title"   : "Services grouped by host groups",
    "table"   : "servicesbyhostgroup",
    "infos"   : [ "host", "service", "hostgroup" ],
    "columns" : [ "hostgroup_alias", "hostgroup_name", 
		  "service_description", "service_plugin_output", "service_state", "service_has_been_checked", 
		  "service_scheduled_downtime_depth", "service_notes_url_expanded", "service_action_url_expanded", 
		  "service_active_checks_enabled", "service_accept_passive_checks", "service_acknowledged", "service_notifications_enabled",
		  "service_comments", "service_is_flapping", "service_is_executing",
                  "host_name", "host_state", "host_has_been_checked", 
		  "service_last_state_change", "service_downtimes", "service_perf_data",
		      "service_max_check_attempts", "service_current_attempt", "service_in_notification_period",
		  "service_scheduled_downtime_depth","service_is_flapping", "service_contacts",
		      ]
}

multisite_datasources["servicegroups"] = {
    "title" : "Servicegroups",
    "table" : "servicegroups",
    "infos" : [ "servicegroup" ],
    "columns" : \
	[ "servicegroup_name", "servicegroup_alias", "servicegroup_num_services", 
	  "servicegroup_num_services_ok", "servicegroup_num_services_warn", 
	  "servicegroup_num_services_crit", "servicegroup_num_services_unknown", 
	  "servicegroup_num_services_pending", "servicegroup_worst_service_state" ],
}

multisite_datasources["hostgroups"] = {
    "title" : "Hostgroups",
    "table" : "hostgroups",
    "infos" : [ "hostgroup" ],
    "columns" :
       	[ "hostgroup_name", "hostgroup_alias", "hostgroup_num_hosts", "hostgroup_num_hosts_up", 
	  "hostgroup_num_hosts_down", "hostgroup_num_hosts_pending", "hostgroup_num_hosts_unreach",
	  "hostgroup_num_services", "hostgroup_num_services_ok", "hostgroup_num_services_warn", 
	  "hostgroup_num_services_crit", "hostgroup_num_services_unknown", "hostgroup_num_services_pending",
	  "hostgroup_worst_service_state" ],
}

