#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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

import htmllib, nagios, time, re, check_mk
from lib import *


def cmp_atoms(s1, s2):
    if s1 < s2:
        return -1
    elif s1 == s2:
        return 0
    else:
        return 1

def cmp_after(x, y):
    if x: return x
    else: return y

def cmp_after3(x, y, z):
    if x: return x
    else: return cmp_after(y, z)

state_indices = {2:0, 3:1, 1:2, 4:3, 0:4}
   
def cmp_svcstate(s1, s2):
    return cmp_atoms(state_indices.get(s1,-1), state_indices.get(s2,-1))

def cmp_svc_hostname_svc(s1, s2):
    try:
      return cmp_after(
        cmp_atoms(s1["host_name"], s2["host_name"]),
        cmp_atoms(s1["description"], s2["description"]))
    except:
       raise Exception("s1: %r, s2: %r" % (s1, s2))

def cmp_svc_severity(s1, s2):
    try:
      return cmp_after3(
        cmp_svcstate(s1["state"], s2["state"]),
        cmp_atoms(s1["last_state_change"], s2["last_state_change"]),
        cmp_svc_hostname_svc(s1, s2))
    except Exception, e:
      raise nagios.MKGeneralException("Cannot compare state of services s1(%r) and s2(%r): %s" % \
		(s1, s2, e))

sort_options = [ ("0", "hostname -> service", cmp_svc_hostname_svc), 
                 ("1", "severity -> status age -> hostname -> service",          cmp_svc_severity, )
                 ]

def enabled_sites(html):
    # If there is only one site (non-multisite), than
    # user cannot enable/disable. 
    configured_sites = check_mk.sites()
    if len(configured_sites) == 1:
	return configured_sites[0]
    sites = []
    for site_name in configured_sites:
	if html.var("site_%s" % site_name) == "on":
	    sites.append(site_name)
    return sites
		 
def page(html):
    global tabs
    tabs = [ ("filter", "Filter"),
             ("results", "Results") ]
    if check_mk.is_allowed_to_act(html.req.user):
       tabs.append(("actions", "Actions"))
    
    # Make search results refresh every 90 seconds
    if html.has_var("results"):
        html.req.headers_out["Refresh"] = "90"

    html.header("Check_mk Multiadmin")

    if html.has_var("filled_in") and not html.has_var("filter"):
        search_filter = build_search_filter(html)
        hits, hosts = nagios.find_entries(search_filter, enabled_sites(html))

    if html.has_var("results"):
        show_tabs(html, tabs, "results")
        show_search_results(html, hits, hosts)

    elif html.has_var("actions"):
        show_tabs(html, tabs, "actions")
        if html.has_var("do_actions"):
            try:
                do_actions(html, hits, hosts)
            except MKUserError, e:
                html.write("<div class=error>%s</div>\n" % e.message)
                html.add_user_error(e.varname, e.message)
                
        if not html.has_var("do_actions") or html.has_users_errors():
            show_action_form(html)
            show_search_results(html, hits, hosts)

    else:
        show_filter_form(html)
        html.write("<p>This filter form allows you to select services by setting "
                   "various filter conditions. After you filled out this form "
                   "please select either the tab <b>Results</b> to see all services "
                   "matching you filter, of <b>Actions</b> to perform actions on "
                   "the selected services.</p>")


    html.footer()
    

def show_tabs(html, tabs, active, suppress_form = False):
    html.write("<table class=tabs cellpadding=0 cellspacing=0><tr>\n")
    if not suppress_form:
        html.begin_form("tabs")
        html.hidden_fields(search_vars)
    for tab, title in tabs:
        if tab == active:
            cssclass = "tabactive"
        else:
            cssclass = "tab"
        html.write("<td>")
        html.button(tab, title, cssclass)
        html.write("</td>")
    if not suppress_form:
        html.end_form()
    
    html.write("<td width=\"100%%\" class=pad>"
               "<b class=headtime>%s</b> "
               "<b>Check_mk Multiadmin</b> "
               "<a href=\"http://mathias-kettner.de/check_mk\">"
               "<img align=absbottom border=0 src=\"check_mk.trans.60.png\">"
               "</a></td></tr></table>" % time.strftime("%H:%M"))

def build_search_filter(html):
    """Constructs Filter: headers for Livestatus according to the current GET
    variables of the search form"""
    search_filter = ""

    # Search texts
    for descr, field in search_textfields:
        value = html.var(field, "").strip()
        if value != "":
	    search_filter += "Filter: " + field + " ~~ " + value + "\n"

    # search dropdown selections
    for descr, field, valuefunc in search_dropdown_fields:
        value = html.var(field, "").strip()
        if value != "":
	    search_filter += "Filter: " + field + " = " + value + "\n"

    # Search out by flags
    for nagios_flag in [ "acknowledged",
                         "is_flapping",
                         "notifications_enabled",
                         "in_notification_period",
			 "checks_enabled" ]:
        current = html.var(nagios_flag, "-1")
        if current != "-1":
	    search_filter += "Filter: " + nagios_flag + " = " + current  + "\n"

    is_summary_host = html.var("is_summary_host")
    if is_summary_host != "-1":
        if is_summary_host == "1":
	    search_filter += "Filter: host_custom_variable_names >= _REALNAME\n"
        else:
	    search_filter += "Filter: host_custom_variable_names < _REALNAME\n"
 
    is_in_downtime = html.var("is_in_downtime")
    if is_in_downtime != "-1":
        if is_in_downtime == "0":
            search_filter += "Filter: scheduled_downtime_depth = 0\n"
	    search_filter += "Filter: host_scheduled_downtime_depth = 0\n"
        else:
            search_filter += "Filter: scheduled_downtime_depth > 0\n"
	    search_filter += "Filter: host_scheduled_downtime_depth > 0\n"
	    search_filter += "Or: 2\n"
            # missing: OR host_scheduled_downtime_depth > 0!

    # Search according to state
    allowed_states = []
    for num, name in nagios.state_names.items():
        if html.var("state%d" % num) != "on":
	    search_filter += "Filter: state != %d\n" % num

    return search_filter

def show_filter_form(html):
    html.begin_form("filter")
    show_tabs(html, tabs, "filter", True)
    html.hidden_field("filled_in", "yes")
    html.write("<table class=form id=filter>\n")

    def select_flag(nagios_flag, deflt, description):
        html.write("<tr><td class=legend>%s</td><td class=content>\n" % description)
        current = html.var(nagios_flag)
        for value, text in [("1", "yes"), ("0", "no"), ("-1", "(ignore)")]:
            if current == value or (current in [ None, ""] and int(value) == deflt):
                checked = " checked"
            else:
                checked = ""
            html.write("<input type=radio name=%s value=\"%s\"%s> %s &nbsp; \n" %
                      (nagios_flag, value, checked, text))
        html.write("</td></tr>\n")

    # Allow site selection on multisite installations
    if check_mk.is_multisite():
	html.write("<tr><td class=legend>Sites</td><td class=content>\n")
	for site_name in check_mk.sites():
	    site = check_mk.site(site_name)
	    html.checkbox("site_" + site_name, 1)
	    html.write(" " + site["alias"] + " &nbsp;")
	html.write("</td></tr>")

    for descr, field in search_textfields:
        html.write("<tr><td class=legend>%s</td>\n"
                  "<td class=content><input name=%s value=\"%s\" type=text class=text></td></tr>"
                  % (descr, field, html.var(field, "")))
        if field == "host_name":
            select_flag("is_summary_host", 0, "Summary Hosts")

    for descr, field, valuefunc in search_dropdown_fields:
         html.write("<tr><td class=legend>%s</td><td class=content>\n" % descr)
	 current = html.var(field, "")
         options = [ ("", "(ignored)") ] + [ (v, v) for v in valuefunc() ]
	 html.select(field, options, current, "") 
	 html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Current State</td>\n"
              "<td class=content>")

    for num, name in nagios.state_names.items():
        varname = "state%d" % num
        val = html.var(varname)
        if val == "on" or html.var("filled_in") != "yes":
            checked = " CHECKED"
        else:
            checked = ""
        html.write("<input type=checkbox name=state%d%s> %s &nbsp;" %
                  (num, checked, name))
    html.write("</td></tr>\n")


    select_flag("acknowledged",                  -1, "Acknowledged")
    select_flag("notifications_enabled",         -1, "Notifications enabled")
    select_flag("checks_enabled",                -1, "Active checks enabled")
    select_flag("is_flapping",                   -1, "Is Flapping")
    select_flag("is_in_downtime",                -1, "Is currently in downtime")
    select_flag("in_notification_period",        -1, "Is currently in notification period")
    
    html.write("</table>")

    html.write("<h2 class=formcaption>Display options</h2>\n")
    html.write("<table class=form id=displayoptions>\n")
    html.write("<tr><td class=legend>Sort order</td>\n"
               "<td class=content>")
    html.select("sortorder", [ o[0:2] for o in sort_options ], html.var("sortorder"), "0")
    html.write("</td></tr>\n")

    html.write("</table>")

    html.write("</form>")
    html.set_focus("search", "description")


def show_action_form(html):
    html.begin_form("actions")
    html.write("<table class=form id=actions>\n")
 
    html.hidden_field("do_actions", "yes")
    html.hidden_field("actions", "yes")

    for var in search_vars:
        html.hidden_field(var, html.var(var))
    
    html.write("<tr><td class=legend>Notifications</td>\n"
               "<td class=content>\n"
               "<input type=submit name=enable_notifications value=\"Enable\"> &nbsp; "
               "<input type=submit name=disable_notifications value=\"Disable\"> &nbsp; "
               "</td></tr>\n")

    html.write("<tr><td class=legend>Active checks</td>\n"
               "<td class=content>\n"
               "<input type=submit name=enable_checks value=\"Enable\"> &nbsp; "
               "<input type=submit name=disable_checks value=\"Disable\"> &nbsp; "
               "<input type=submit name=resched_checks value=\"Reschedule next check now\"></td></tr>\n"
               "</td></tr>\n")

    html.write("<tr><td rowspan=2 class=legend>Acknowledge</td>\n")
    html.write("<td class=content><input type=submit name=acknowledge value=\"Acknowledge\"> &nbsp; "
               "<input type=submit name=remove_ack value=\"Remove Acknowledgement\"></td></tr><tr>"
               "<td class=content><div class=textinputlegend>Comment:</div>")
    html.text_input("comment")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend rowspan=3>Schedule Downtimes</td>\n"
               "<td class=content>\n"
               "<input type=submit name=down_2h value=\"2 hours\"> "
               "<input type=submit name=down_today value=\"Today\"> "
               "<input type=submit name=down_week value=\"This week\"> "
               "<input type=submit name=down_month value=\"This month\"> "
               "<input type=submit name=down_year value=\"This year\"> "
               " &nbsp; - &nbsp;"
               "<input type=submit name=down_remove value=\"Remove all\"> "
               "</tr><tr>"
               "<td class=content>"
               "<input type=submit name=down_custom value=\"Custom time range\"> &nbsp; ")
    html.datetime_input("down_from", time.time())
    html.write("&nbsp; to &nbsp;")
    html.datetime_input("down_to", time.time() + 7200)
    html.write("</td></tr>")
    html.write("<tr><td class=content><div class=textinputlegend>Comment:</div>\n")
    html.text_input("down_comment")
    html.write("</td></tr>")


    html.write("</table></form>\n")


def show_search_results(html, services, hosts):
    sortorder = html.var("sortorder", "0")
    sortcmp = sort_options[0][2]
    sortname = sort_options[0][1]
    for idname, description, comp in sort_options:
        if idname == sortorder:
            sortcmp = comp
            sortname = description
            break

    html.write("%d matching services on %d hosts, sort order: %s" % (len(services), len(hosts), sortname))
    html.write("<table class=services>\n")
    
    services.sort(sortcmp)

    last_hostname = None
    odd = False
    num_hosts_down = 0
    at_least_one_state = {}
    for hit in services:
        odd = not odd
        state = int(hit["state"])
        if odd:
            trclass = "odd"
        else:
            trclass = "even"
        trclass += str(state)

        hostname = hit["host_name"]
	host_state = hit["host_state"]
        last_change = int(hit["last_state_change"])
        
        # ack = hit["acknowledged"] != 0
        age = time.time() - last_change
        if age < 60 * 10:
            age_class = "agerecent"
        else:
            age_class = "age"

        if hostname != last_hostname:
            # http://10.10.0.141/nagios/cgi-bin/status.cgi?host=Acht
            if host_state == 0:
                hoststate = "up"
            else:
                hoststate = "down"
		num_hosts_down += 1
            host_url = html.req.defaults["nagios_cgi_url"] + "/status.cgi?host=" + htmllib.urlencode(hostname)
            html.write("<tr><td class=host colspan=4>"
                       "<b class=%s>"
                       "<a href=\"%s\">%s</a></b></td></tr>\n" % (hoststate, host_url, hostname))
        last_hostname = hostname
        html.write("<tr class=%s>" % trclass)

        # Current state
        statename = nagios.short_state_names[state]
	at_least_one_state[state] = True	

        svc_url = html.req.defaults["nagios_cgi_url"] + \
                  ( "/extinfo.cgi?type=2&host=%s&service=%s" % (hostname, htmllib.urlencode(hit["description"])))
        html.write("<td class=state%d>%s</td>\n" % (state, statename))
        html.write("<td><a href=\"%s\">%s</a></td>\n" % (svc_url, hit["description"]))
        html.write("<td class=%s>%s</td>\n" % (age_class, html.age_text(age)))
        html.write("<td>%(plugin_output)s</td></tr>\n" % hit)

    html.write("</table>\n")

    sound = None
    if num_hosts_down > 0:
        sound = "host"
    elif at_least_one_state.get(2):
	sound = "critical"
    elif at_least_one_state.get(1):
	sound = "warning"
    elif at_least_one_state.get(3):
	sound = "unknown"
    else:
	sound = "ok"

    if sound:
	try:
	    sound_uri = check_mk.multiadmin_sounds[sound]
	    html.write('<p><b>BUMM: %s(%s)!!!</b></p>' % (sound, sound_uri))
	    html.write('<object type="audio/x-wav" data="%s" height="0" width="0">'
		    '<param name="filename" value="%s">'
		    '<param name="autostart" value="true"><param name="playcount" value="1"></object>' % (sound_uri, sound_uri))
        except:
	    pass


def do_actions(html, hits, hosts):
    if not check_mk.is_allowed_to_act(html.req.user):
       html.write("<div class=error>"
	     "You are not allowed to perform actions. If you think this is an error, "
             "please ask your administrator to add your login to <tt>multiadmin_action_users</tt> "
	     "in <tt>main.mk</tt></div>")
       return
    count = 0
    pipe = file(html.req.defaults["nagios_command_pipe_path"], "w")
    command = None
    for hit in hits:
        title, nagios_commands = nagios_service_action_command(html, hit)
        if not html.has_var("do_action_really"):
            html.write("<div class=really>Do you really want to %s "
                       "the following %d services?" % (title, len(hits)))
            html.begin_form("confirm")
            html.hidden_fields()
            html.button("do_action_really", "Yes!", "really")
            html.end_form()
            html.write("</div>")
            show_search_results(html, hits, hosts)
            return
        for command in nagios_commands:
            pipe.write(command)
            count += 1
    if command:
        html.write("<div class=success>Successfully sent %d commands to Nagios. " % count)
        html.write("The last one was: <pre>%s</pre></div>" % command)
    else:
        html.write("<div class=success>No matching service. No command sent.</div>")


def nagios_service_action_command(html, service):
    host = service["host_name"]
    descr = service["description"]
    down_from = time.time()
    down_to = None

    if html.var("enable_notifications"):
        command = "ENABLE_SVC_NOTIFICATIONS;%s;%s" % (host, descr)
        title = "<b>enable notifications</b> for"

    elif html.var("disable_notifications"):
        command = "DISABLE_SVC_NOTIFICATIONS;%s;%s" % (host, descr)
        title = "<b>disable notifications</b> for"

    elif html.var("enable_checks"):
        command = "ENABLE_SVC_CHECK;%s;%s" % (host, descr)
        title = "<b>enable active checks</b> of"

    elif html.var("disable_checks"):
        command = "DISABLE_SVC_CHECK;%s;%s" % (host, descr)
        title = "<b>disable active checks</b> of"

    elif html.var("resched_checks"):
        command = "SCHEDULE_FORCED_SVC_CHECK;%s;%s;%d" % (host, descr, int(time.time()))
        title = "<b>reschedule an immediate check</b> of"

    elif html.var("acknowledge"):
        comment = html.var("comment")
        if not comment:
            raise MKUserError("comment", "You need to supply a comment.")
        command = "ACKNOWLEDGE_SVC_PROBLEM;%s;%s;2;1;0;%s" % \
                  (host, descr, html.req.user) + ";" + html.var("comment")
        title = "<b>acknowledge the problems</b> of"

    elif html.var("remove_ack"):
        command = "REMOVE_SVC_ACKNOWLEDGEMENT;%s;%s" % (host, descr)
        title = "<b>remove acknowledgements</b> from"

    elif html.var("down_2h"):
        down_to = down_from + 7200
        title = "<b>schedule an immediate 2-hour downtime</b> on"

    elif html.var("down_today"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = "<b>schedule an immediate downtime until 24:00:00</b> on"

    elif html.var("down_week"):
        br = time.localtime(down_from)
        wday = br.tm_wday
        days_plus = 6 - wday
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        down_to += days_plus * 24 * 3600
        title = "<b>schedule an immediate downtime until sunday night</b> on"

    elif html.var("down_month"):
        br = time.localtime(down_from)
        new_month = br.tm_mon + 1
        if new_month == 13:
            new_year = br.tm_year + 1
            new_month = 1
        else:
            new_year = br.tm_year
        down_to = time.mktime((new_year, new_month, 1, 0, 0, 0, 0, 0, br.tm_isdst)) 
        title = "<b>schedule an immediate downtime until end of month</b> on"

    elif html.var("down_year"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, 12, 31, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = "<b>schedule an immediate downtime until end of %d</b> on" % br.tm_year

    elif html.var("down_custom"):
        down_from = html.get_datetime_input("down_from")
        down_to   = html.get_datetime_input("down_to")
        title = "<b>schedule a downtime from %s to %s</b> on " % (
            time.asctime(time.localtime(down_from)),
            time.asctime(time.localtime(down_to)))

    elif html.var("down_remove"):
        downtime_ids = []
	for id in service["downtimes"]:
	   if id != "":
	       downtime_ids.append(int(id))
        commands = []
        for dtid in downtime_ids:
            commands.append("[%d] DEL_SVC_DOWNTIME;%d\n" % (int(time.time()), dtid))
        title = "<b>remove all scheduled downtimes</b> of "
        return title, commands

    else:
        raise MKUserError(None, "Sorry. This command is not implemented.")

    if down_to:
        comment = html.var("down_comment")
        if not comment:
            raise MKUserError("down_comment", "You need to supply a comment for your downtime.")
        command = ("SCHEDULE_SVC_DOWNTIME;%s;%s;" % (host, descr) \
                   + ("%d;%d;1;0;0;%s;" % (int(down_from), int(down_to), html.req.user)) \
                   + comment)
                  
    nagios_command = ("[%d] " % int(time.time())) + command + "\n"
    return title, [nagios_command]

def all_check_commands():
   commands = nagios.query_livestatus_column_unique("GET commands\nColumns: name\n")
   commands.sort()
   return commands

# HTML variables set by search dialog. They need to be
# conserved over all sub pages
search_vars = [ "filled_in",
                "description",
                "host_name",
                "check_command",
                "plugin_output",
                "state0",
                "state1",
                "state2",
                "state3",
                "state4",
                "acknowledged",
                "notifications_enabled",
                "is_in_downtime",
                "is_flapping",
                "is_summary_host",
		"checks_enabled",
                "in_notification_period",
                "sortorder",
                ] + [ "site_%s" % n for n in check_mk.sites() ]

search_textfields = [ ("Service",       "description"),
                      ("Hostname",      "host_name"),
                      ("Check output",  "plugin_output"),
                      ]

search_dropdown_fields = [ ("Check command", "check_command", all_check_commands) ]
