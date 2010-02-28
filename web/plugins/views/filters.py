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



# Filters for substring search, displaying a text input field
class FilterText(Filter):
    def __init__(self, name, title, info, column, htmlvar, op):
	Filter.__init__(self, name, title, info, [htmlvar])
	self.op = op
	self.column = column
    
    def display(self):
	htmlvar = self.htmlvars[0]
	current_value = html.var(htmlvar, "")
	html.text_input(htmlvar, current_value)

    def filter(self, infoname):
	htmlvar = self.htmlvars[0]
	current_value = html.var(htmlvar)
	if current_value:
	    return "Filter: %s %s %s\n" % (self.column, self.op, current_value)
	else:
	    return ""

    def variable_settings(self, row):
       return [ (self.htmlvars[0], row[self.column]) ]

    def heading_info(self, infoname):
	htmlvar = self.htmlvars[0]
	return html.var(self.htmlvars[0])

#                               filter          title              info       column           htmlvar
declare_filter(100, FilterText("hostregex",    "Hostname",        "host",    "host_name",      "host",    "~~"),
			  "Search field allowing regular expressions and partial matches")

declare_filter(101, FilterText("host",    "Hostname",             "host",    "host_name",          "host",    "="),
			  "Exact match, used for linking")

declare_filter(200, FilterText("serviceregex", "Service",         "service", "service_description",   "service", "~~"),
			  "Search field allowing regular expressions and partial matches")

declare_filter(201, FilterText("service", "Service",              "service", "service_description",   "service", "="),
		          "Exact match, used for linking")

declare_filter(202, FilterText("output",  "Service check output", "service", "service_plugin_output", "service_output", "~~"))


class FilterLimit(Filter):
    def __init__(self):
	Filter.__init__(self, "limit", "Limit number of data sets", None, [ "limit" ])

    def current_value(self):
	try:
	    return int(html.var("limit"))
	except:
	    return 0

    def display(self):
	html.number_input("limit", self.current_value())
    
    def filter(self, infoname):
	v = self.current_value()
	if v > 0:
	    return "Limit: %d\n" % v
	return ""

declare_filter(300, FilterLimit(), "Limits the number of items queried via livestatus. The limitation is "
	"done <b>before</b> any sorting is done.")
	

# Helper that retrieves the list of host/service/contactgroups via Livestatus
def all_groups(what):
    groups = dict(html.live.query("GET %sgroups\nColumns: name alias\n" % what))
    names = groups.keys()
    names.sort()
    return [ (name, groups[name]) for name in names ]

class FilterGroupCombo(Filter):
    def __init__(self, what, enforce):
	self.enforce = enforce
	self.prefix = not self.enforce and "opt" or ""
	Filter.__init__(self, self.prefix + what + "group", # name,     e.g. "hostgroup"
		what[0].upper() + what[1:] + "group",       # title,    e.g. "Hostgroup"
		what,                                       # info,     e.g. "host"
		[ self.prefix + what + "group" ])           # htmlvars, e.g. "hostgroup" 
        self.what = what

    def display(self):
	choices = all_groups(self.what)
	if not self.enforce:
	    choices = [("", "")] + choices
	html.select(self.htmlvars[0], choices)

    def current_value(self, infoname):
	htmlvar = self.htmlvars[0]
	return html.var(htmlvar)

    def filter(self, infoname):
	current_value = self.current_value(infoname)
    	if not current_value: 
	    if not self.enforce:
		return ""
            # Take first group with the name we search
	    current_value = html.live.query_value("GET %sgroups\nColumns: name\nLimit: 1\n" % self.what, None)

	if current_value == None:
	    return "" # no {what}group exists!

	if self.what + "s" == infoname:
	    col = "groups"
	else:
	    col = self.what + "_groups"
	return "Filter: %s >= %s\n" % (col, current_value)

    def variable_settings(self, row):
	varname = self.htmlvars[0]
	value = row.get(self.what + "group_name")
	if value:
	    return [(varname, value)]
	else:
	    return []
    
    def heading_info(self, infoname):
	current_value = self.current_value(infoname)
	if current_value:
	    alias = html.live.query_value("GET %sgroups\nColumns: alias\nFilter: name = %s\n" % 
		(self.what, current_value))
	    return alias


declare_filter(104, FilterGroupCombo("host",    True),  "Dropdown list, selection of host group is <b>enforced</b>")
declare_filter(204, FilterGroupCombo("service", True),  "Dropdown list, selection of service group is <b>enforced</b>")
declare_filter(105, FilterGroupCombo("host",    False), "Optional selection of host group")
declare_filter(205, FilterGroupCombo("service", False), "Optional selection of service group")
# Livestatus still misses "contact_groups" column. 
# declare_filter(FilterGroupCombo("contact"))

class FilterQueryDropdown(Filter):
    def __init__(self, name, title, info, query, filterline):
	Filter.__init__(self, name, title, info, [ name ])
	self.query = query
	self.filterline = filterline

    def display(self):
	selection = html.live.query_column_unique(self.query)
	html.sorted_select(self.name, [("", "")] + [(x,x) for x in selection])

    def filter(self, infoname):
	current = html.var(self.name)
	if current:
	    return self.filterline % current
	else:
	    return ""

declare_filter(110, FilterQueryDropdown("host_check_command", "Host check command", "host", \
	"GET commands\nColumns: name\n", "Filter: host_check_command = %s\n"))
declare_filter(210, FilterQueryDropdown("check_command", "Service check command", "service", \
	"GET commands\nColumns: name\n", "Filter: service_check_command = %s\n"))

class FilterServiceState(Filter):
    def __init__(self):
	Filter.__init__(self, "svcstate", "Service states", 
		"service", [ "st0", "st1", "st2", "st3", "stp" ])
    
    def display(self):
	if html.var("filled_in"):
	    defval = ""
	else:
	    defval = "on"
	for var, text in [("st0", "OK"), ("st1", "WARN"), ("st2", "CRIT"), ("st3", "UNKNOWN"), ("stp", "PENDING")]:
	    html.checkbox(var, defval)
	    html.write(" %s " % text)

    def filter(self, infoname):
	headers = []
	if html.var("filled_in"):
	    defval = ""
	else:
	    defval = "on"

	for i in [0,1,2,3]:
	    if html.var("st%d" % i, defval) == "on":
		headers.append("Filter: service_state = %d\nFilter: service_has_been_checked = 1\nAnd: 2\n" % i)
	if html.var("stp", defval) == "on":
	    headers.append("Filter: service_has_been_checked = 0\n")
	if len(headers) == 0:
	    return "Limit: 0\n" # not allowed state
	else:
	    return "".join(headers) + ("Or: %d\n" % len(headers))
	
declare_filter(215, FilterServiceState())

class FilterHostState(Filter):
    def __init__(self):
	Filter.__init__(self, "hoststate", "Host states", 
		"host", [ "st0", "st1", "st2", "stp" ])
    
    def display(self):
	if html.var("filled_in"):
	    defval = ""
	else:
	    defval = "on"
	for var, text in [("st0", "UP"), ("st1", "DOWN"), ("st2", "UNREACH"), ("stp", "PENDING")]:
	    html.checkbox(var, defval)
	    html.write(" %s " % text)

    def filter(self, infoname):
	headers = []
	if html.var("filled_in"):
	    defval = ""
	else:
	    defval = "on"

	for i in [0,1,2]:
	    if html.var("st%d" % i, defval) == "on":
		headers.append("Filter: host_state = %d\nFilter: host_has_been_checked = 1\nAnd: 2\n" % i)
	if html.var("stp", defval) == "on":
	    headers.append("Filter: host_has_been_checked = 0\n")
	if len(headers) == 0:
	    return "Limit: 0\n" # not allowed state
	else:
	    return "".join(headers) + ("Or: %d\n" % len(headers))

declare_filter(115, FilterHostState())

class FilterTristate(Filter):
    def __init__(self, name, title, info, column, deflt = -1):
	self.column = column
	self.varname = "is_" + name
	Filter.__init__(self, name, title, info, [ self.varname ])
	self.deflt = deflt
   
    def display(self):
        current = html.var(self.varname)
        for value, text in [("1", "yes"), ("0", "no"), ("-1", "(ignore)")]:
            checked = current == value or (current in [ None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text)

    def tristate_value(self):
        current = html.var(self.varname)
	if current in [ None, "" ]:
	    return self.deflt
	return int(current)
	
    def filter(self, infoname):
	current = self.tristate_value()
	if current == -1: # ignore
	    return ""
	elif current == 1:
	    return self.filter_code(infoname, True)
	else:
	    return self.filter_code(infoname, False)

class FilterNagiosFlag(FilterTristate):
    def __init__(self, info, column, title, deflt = -1):
	FilterTristate.__init__(self, column, title, info, column, deflt)

    def filter_code(self, infoname, positive):
	if positive:
	    return "Filter: %s != 0\n" % self.column
	else:
	    return "Filter: %s = 0\n" % self.column

class FilterNagiosExpression(FilterTristate):
    def __init__(self, info, name, title, pos, neg, deflt = -1):
	FilterTristate.__init__(self, name, title, info, None, deflt)
	self.pos = pos
	self.neg = neg

    def filter_code(self, infoname, positive):
	return positive and self.pos or self.neg

declare_filter(120, FilterNagiosExpression("host", "summary_host", "Show summary hosts", 
	    "Filter: host_custom_variable_names >= _REALNAME\n",
	    "Filter: host_custom_variable_names < _REALNAME\n"))


declare_filter(130, FilterNagiosFlag("host",    "host_in_notification_period",   "Host is in notification period"))
declare_filter(230, FilterNagiosFlag("service", "service_acknowledged",             "Problem has been acknowledged"))
declare_filter(231, FilterNagiosFlag("service", "service_in_notification_period",   "Service is in notification period"))
declare_filter(232, FilterNagiosFlag("service", "service_active_checks_enabled",    "Active checks enabled"))
declare_filter(233, FilterNagiosFlag("service", "service_notifications_enabled",    "Notifications enabled"))
declare_filter(236, FilterNagiosFlag("service", "service_is_flapping",              "Flapping"))
declare_filter(131, FilterNagiosFlag("host",    "host_in_notification_period",   "Host is in notification period"))
declare_filter(231, FilterNagiosFlag("service", "service_scheduled_downtime_depth", "Service in downtime"))
declare_filter(132, FilterNagiosFlag("host",    "host_scheduled_downtime_depth", "Host in downtime"))
declare_filter(232, FilterNagiosExpression("service", "in_downtime", "Host or Service in downtime",
	    "Filter: service_scheduled_downtime_depth > 0\nFilter: host_scheduled_downtime_depth > 0\nOr: 2\n",
	    "Filter: service_scheduled_downtime_depth = 0\nFilter: host_scheduled_downtime_depth = 0\nAnd: 2\n"))
	

class FilterSite(Filter):
    def __init__(self, name, enforce):
	Filter.__init__(self, name, "Site", None, ["site"])
	self.enforce = enforce

    def display(self):
	site_selector(html, "site", self.enforce)

    def filter(self, infoname):
	if config.is_multisite():
	    site = html.var("site")
	    if site:
		return "Sites: %s\n" % html.var("site", "")
	    elif not self.enforce:
		return ""
	    else:
		return "Sites:\n" # no site at all
	else:
	    return ""

    def heading_info(self, infoname):
	current_value = html.var("site")
	if current_value:
	    alias = config.site(current_value)["alias"]
	    return alias
    
    def variable_settings(self, row):
	return [("site", row["site"])]
	
declare_filter(500, FilterSite("site",    True), "Selection of site is enforced, use this filter for joining")
declare_filter(501, FilterSite("siteopt", False), "Optional selection of a site")
