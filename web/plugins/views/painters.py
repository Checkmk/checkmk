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
# Painters
##################################################################################
def nagios_host_url(sitename, host):
    nagurl = config.site(sitename)["nagios_cgi_url"]
    return nagurl + "/status.cgi?host=" + htmllib.urlencode(host)

def nagios_service_url(sitename, host, svc):
    nagurl = config.site(sitename)["nagios_cgi_url"]
    return nagurl + ( "/extinfo.cgi?type=2&host=%s&service=%s" % (htmllib.urlencode(host), htmllib.urlencode(svc)))

def paint_age(timestamp, has_been_checked, bold_if_younger_than):
    if not has_been_checked:
	return "age", "-"
	   
    age = time.time() - timestamp
    if age < bold_if_younger_than: 
	age_class = "agerecent"
    else:
	age_class = "age"
    return age_class, html.age_text(age)

def paint_site_icon(row):
    if row["site"] and config.use_siteicons:
	return None, "<img class=siteicon src=\"icons/site-%s-24.png\">" % row["site"]
    else:
	return None, ""
	

multisite_painters["sitename_plain"] = {
    "title" : "Site id",
    "short" : "Site",
    "columns" : ["site"],
    "paint" : lambda row: (None, row["site"])
}

multisite_painters["sitealias"] = {
    "title" : "Site alias",
    "columns" : ["site"],
    "paint" : lambda row: (None, config.site(row["site"])["alias"])
}

def paint_host_black(row):
    state = row["host_state"]
    if state == 0:
	style = "up"
    else:
	style = "down"
    return "host", "<b class=%s><a href=\"%s\">%s</a></b>" % \
	(style, nagios_host_url(row["site"], row["host_name"]), row["host_name"])

multisite_painters["host_black"] = {
    "title" : "Hostname, red background if down or unreachable",
    "short" : "Host",
    "columns" : ["site","host_name"],
    "paint" : paint_host_black,
}

multisite_painters["host_with_state"] = {
    "title" : "Hostname colored with state",
    "short" : "Host",
    "columns" : ["site","host_name"],
    "paint" : lambda row: ("state hstate hstate%d" % row["host_state"], row["host_name"])
}

multisite_painters["host"] = {
    "title" : "Hostname",
    "short" : "Host",
    "columns" : ["host_name"],
    "paint" : lambda row: (None, row["host_name"])
}

multisite_painters["alias"] = {
    "title" : "Host alias",
    "short" : "Alias",
    "columns" : ["host_alias"],
    "paint" : lambda row: (None, row["host_alias"])
}

def paint_service_state_short(row):
    if row["service_has_been_checked"] == 1:
	state = row["service_state"]
	name = nagios_short_state_names[row["service_state"]]
    else:
	state = "p"
	name = "PEND"
    return "state svcstate state%s" % state, name

def paint_host_state_short(row):
# return None, str(row)
    if row["host_has_been_checked"] == 1:
	state = row["host_state"]
	name = nagios_short_host_state_names[row["host_state"]]
    else:
	state = "p"
	name = "PEND"
    return "state hstate hstate%s" % state, name

multisite_painters["service_state"] = {
    "title" : "Service state",
    "short" : "State",
    "columns" : ["service_has_been_checked","service_state"],
    "paint" : paint_service_state_short
}

multisite_painters["host_state"] = {
    "title" : "Host state",
    "short" : "state",
    "columns" : ["host_has_been_checked","host_state"],
    "paint" : paint_host_state_short
}

multisite_painters["site_icon"] = {
    "title" : "Icon showing the site",
    "short" : "",
    "columns" : ["site"],
    "paint" : paint_site_icon
}

multisite_painters["svc_plugin_output"] = {
    "title" : "Output of check plugin",
    "short" : "Status detail",
    "columns" : ["service_plugin_output"],
    "paint" : lambda row: (None, row["service_plugin_output"])
}
multisite_painters["svc_perf_data"] = {
    "title" : "Service performance data",
    "short" : "Perfdata",
    "columns" : ["service_perf_data"],
    "paint" : lambda row: (None, row["service_perf_data"])
}
    
multisite_painters["svc_contacts"] = {
    "title" : "Service contacts",
    "short" : "Contacts",
    "columns" : ["contacts"],
    "paint" : lambda row: (None, ", ".join(row["service_contacts"]))
}

multisite_painters["host_plugin_output"] = {
    "title" : "Output of host check plugin",
    "short" : "Status detail",
    "columns" : ["host_plugin_output"],
    "paint" : lambda row: (None, row["host_plugin_output"])
}
multisite_painters["service_description"] = {
    "title" : "Service description",
    "short" : "Service",
    "columns" : ["service_description"],
    "paint" : lambda row: (None, row["service_description"])
}

multisite_painters["svc_state_age"] = {
    "title" : "The age of the current service state",
    "short" : "Age",
    "columns" : [ "service_has_been_checked", "service_last_state_change" ],
    "paint" : lambda row: paint_age(row["service_last_state_change"], row["service_has_been_checked"] == 1, 60 * 10)
}
multisite_painters["svc_check_age"] = {
    "title" : "The time since the last check of the service",
    "short" : "Checked",
    "columns" : [ "service_has_been_checked", "service_last_check" ],
    "paint" : lambda row: paint_age(row["service_last_check"], row["service_has_been_checked"] == 1, 0)
}

multisite_painters["svc_attempt"] = {
    "title" : "Current check attempt",
    "short" : "Att.",
    "columns" : [ "service_current_attempt", "service_max_check_attempts" ],
    "paint" : lambda row: (None, "%d/%d" % (row["service_current_attempt"], row["service_max_check_attempts"]))
}

def paint_nagiosflag(row, field, bold_if_nonzero):
    value = row[field]
    yesno = {True:"yes", False:"no"}[value != 0]
    if (value != 0) == bold_if_nonzero:
	return "badflag", yesno
    else:
	return "goodflag", yesno

multisite_painters["svc_in_downtime"] = {
    "title" : "Currently in downtime",
    "short" : "Dt.",
    "columns" : [ "service_scheduled_downtime_depth" ],
    "paint" : lambda row: paint_nagiosflag(row, "service_scheduled_downtime_depth", True)
}
multisite_painters["svc_in_notifper"] = {
    "title" : "In notification period",
    "short" : "in notif. p.",
    "columns" : [ "service_in_notification_period" ],
    "paint" : lambda row: paint_nagiosflag(row, "service_in_notification_period", False)
}
multisite_painters["svc_flapping"] = {
    "title" : "Is flapping",
    "short" : "flap",
    "columns" : [ "service_is_flapping" ],
    "paint" : lambda row: paint_nagiosflag(row, "service_is_flapping", True)
}


def paint_svc_count(id, count):
    if count > 0:
	return "count svcstate state%s" % id, str(count)
    else:
	return "count svcstate statex", "0"

def paint_host_count(id, count):
    if count > 0:
	return "count hstate hstate%s" % id, str(count)
    else:
	return "count hstate hstatex", "0"

multisite_painters["num_services"] = {
    "title"   : "Number of services",
    "short"   : "",
    "columns" : [ "host_num_services" ],
    "paint"   : lambda row: (None, str(row["host_num_services"])),
}

multisite_painters["num_services_ok"] = {
    "title"   : "Number of services in state OK",
    "short"   : "O",
    "columns" : [ "host_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["host_num_services_ok"])
}

multisite_painters["num_services_warn"] = {
    "title"   : "Number of services in state WARN",
    "short"   : "W",
    "columns" : [ "host_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["host_num_services_warn"])
}

multisite_painters["num_services_crit"] = {
    "title"   : "Number of services in state CRIT",
    "short"   : "C",
    "columns" : [ "host_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["host_num_services_crit"])
}

multisite_painters["num_services_unknown"] = {
    "title"   : "Number of services in state UNKNOWN",
    "short"   : "U",
    "columns" : [ "host_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["host_num_services_unknown"])
}

multisite_painters["num_services_pending"] = {
    "title"   : "Number of services in state PENDING",
    "short"   : "P",
    "columns" : [ "host_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["host_num_services_pending"])
}

#    _   _           _                                  
#   | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___ 
#   | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#   |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#   |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                       |___/                |_|        
#
multisite_painters["hg_num_services"] = {
    "title"   : "Number of services",
    "short"   : "",
    "columns" : [ "hostgroup_num_services" ],
    "paint"   : lambda row: (None, str(row["hostgroup_num_services"])),
}

multisite_painters["hg_num_services_ok"] = {
    "title"   : "Number of services in state OK",
    "short"   : "O",
    "columns" : [ "hostgroup_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["hostgroup_num_services_ok"])
}

multisite_painters["hg_num_services_warn"] = {
    "title"   : "Number of services in state WARN",
    "short"   : "W",
    "columns" : [ "hostgroup_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["hostgroup_num_services_warn"])
}

multisite_painters["hg_num_services_crit"] = {
    "title"   : "Number of services in state CRIT",
    "short"   : "C",
    "columns" : [ "hostgroup_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["hostgroup_num_services_crit"])
}

multisite_painters["hg_num_services_unknown"] = {
    "title"   : "Number of services in state UNKNOWN",
    "short"   : "U",
    "columns" : [ "hostgroup_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["hostgroup_num_services_unknown"])
}

multisite_painters["hg_num_services_pending"] = {
    "title"   : "Number of services in state PENDING",
    "short"   : "P",
    "columns" : [ "hostgroup_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["hostgroup_num_services_pending"])
}
multisite_painters["hg_num_hosts_up"] = {
    "title"   : "Number of hosts in state UP",
    "short"   : "Up",
    "columns" : [ "hostgroup_num_hosts_up" ],
    "paint"   : lambda row: paint_host_count(0, row["hostgroup_num_hosts_up"])
}
multisite_painters["hg_num_hosts_down"] = {
    "title"   : "Number of hosts in state DOWN",
    "short"   : "Dw",
    "columns" : [ "hostgroup_num_hosts_down" ],
    "paint"   : lambda row: paint_host_count(0, row["hostgroup_num_hosts_down"])
}
multisite_painters["hg_num_hosts_unreach"] = {
    "title"   : "Number of hosts in state UNREACH",
    "short"   : "Un",
    "columns" : [ "hostgroup_num_hosts_unreach" ],
    "paint"   : lambda row: paint_host_count(0, row["hostgroup_num_hosts_unreach"])
}
multisite_painters["hg_num_hosts_pending"] = {
    "title"   : "Number of hosts in state PENDING",
    "short"   : "Un",
    "columns" : [ "hostgroup_num_hosts_pending" ],
    "paint"   : lambda row: paint_host_count(0, row["hostgroup_num_hosts_pending"])
}
multisite_painters["hg_name"] = {
    "title" : "Hostgroup name",
    "short" : "Name",
    "columns" : ["hostgroup_name"],
    "paint" : lambda row: (None, row["hostgroup_name"])
}
multisite_painters["hg_alias"] = {
    "title" : "Hostgroup alias",
    "short" : "Alias",
    "columns" : ["hostgroup_alias"],
    "paint" : lambda row: (None, row["hostgroup_alias"])
}

#    ____                  _                                          
#   / ___|  ___ _ ____   _(_) ___ ___  __ _ _ __ ___  _   _ _ __  ___ 
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \/ _` | '__/ _ \| | | | '_ \/ __|
#    ___) |  __/ |   \ V /| | (_|  __/ (_| | | | (_) | |_| | |_) \__ \
#   |____/ \___|_|    \_/ |_|\___\___|\__, |_|  \___/ \__,_| .__/|___/
#                                     |___/                |_|        

multisite_painters["sg_num_services"] = {
    "title"   : "Number of services",
    "short"   : "",
    "columns" : [ "servicegroup_num_services" ],
    "paint"   : lambda row: (None, str(row["servicegroup_num_services"])),
}

multisite_painters["sg_num_services_ok"] = {
    "title"   : "Number of services in state OK",
    "short"   : "O",
    "columns" : [ "servicegroup_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["servicegroup_num_services_ok"])
}

multisite_painters["sg_num_services_warn"] = {
    "title"   : "Number of services in state WARN",
    "short"   : "W",
    "columns" : [ "servicegroup_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["servicegroup_num_services_warn"])
}

multisite_painters["sg_num_services_crit"] = {
    "title"   : "Number of services in state CRIT",
    "short"   : "C",
    "columns" : [ "servicegroup_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["servicegroup_num_services_crit"])
}

multisite_painters["sg_num_services_unknown"] = {
    "title"   : "Number of services in state UNKNOWN",
    "short"   : "U",
    "columns" : [ "servicegroup_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["servicegroup_num_services_unknown"])
}

multisite_painters["sg_num_services_pending"] = {
    "title"   : "Number of services in state PENDING",
    "short"   : "P",
    "columns" : [ "servicegroup_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["servicegroup_num_services_pending"])
}
multisite_painters["sg_name"] = {
    "title" : "Servicegroup name",
    "short" : "Name",
    "columns" : ["servicegroup_name"],
    "paint" : lambda row: (None, row["servicegroup_name"])
}
multisite_painters["sg_alias"] = {
    "title" : "Servicegroup alias",
    "short" : "Alias",
    "columns" : ["servicegroup_alias"],
    "paint" : lambda row: (None, row["servicegroup_alias"])
}

# Intelligent Links to PNP4Nagios 0.6.X

def paint_pnp_service_link(row):
    # On our local site, we look for an existing XML file or PNP.
    sitename = row["site"]
    site = html.site_status[sitename]["site"]
    host = row["host_name"]
    svc = row["service_description"]
    url = site["pnp_prefix"] + ("?host=%s&srv=%s" % (htmllib.urlencode(host), htmllib.urlencode(svc)))
    a = "<a href=\"%s\">PNP</a>" % url

    if config.site_is_local(sitename):
	# Where is our RRD?
	basedir = config.defaults["rrd_path"] + "/" + host
	xmlpath = basedir + "/" + svc.replace("/", "_").replace(" ", "_") + ".xml"
	if os.path.exists(xmlpath):
	    return "", a
	else:
	    return "", ""
    
    # Darn. Remote site. We cannot check for a file but rather use
    # (Lars' idea) the perfdata field
    elif row["service_perf_data"]:
	return "", a
    else:
	return "", ""
        

multisite_painters["link_to_pnp_service"] = {
    "title"   : "Link to PNP4Nagios",
    "short"   : "PNP",
    "columns" : [ "site", "host_name", "service_description", "service_perf_data"],
    "paint"   : paint_pnp_service_link,
}


