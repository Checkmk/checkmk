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

import socket, config, defaults, re, time
from lib import *

# TODO: make this configurable and thus work for non OMD-users as
# well.
try:
    socket_path = defaults.omd_root + "/tmp/run/mkeventd/status"
    pipe_path = defaults.omd_root + "/tmp/run/mkeventd/events"
except:
    run_dir = defaults.livestatus_unix_socket.rsplit("/",1)[0]
    socket_path = run_dir + "/mkeventd/status"
    pipe_path = run_dir + "/mkeventd/events"

syslog_priorities = [
    (0, "emerg" ),
    (1, "alert" ),
    (2, "crit" ),
    (3, "err" ),
    (4, "warning" ),
    (5, "notice" ),
    (6, "info" ),
    (7, "debug" ),
]

syslog_facilities = [
    (0, "kern"),
    (1, "user"),
    (2, "mail"),
    (3, "daemon"),
    (4, "auth"),
    (5, "syslog"),
    (6, "lpr"),
    (7, "news"),
    (8, "uucp"),
    (9, "cron"),
    (10, "authpriv"),
    (11, "ftp"),
    (12, "(12: unused)"),
    (13, "(13: unused)"),
    (14, "(14: unused)"),
    (15, "(15: unused)"),
    (16, "local0"),
    (17, "local1"),
    (18, "local2"),
    (19, "local3"),
    (20, "local4"),
    (21, "local5"),
    (22, "local6"),
    (23, "local7"),
]

phase_names = {
    'counting' : _("counting"),
    'delayed'  : _("delayed"),
    'open'     : _("open"),
    'ack'      : _("acknowledged"),
}

action_whats = {
  "ORPHANED"     : _("Event deleted in counting state because rule was deleted."),
  "NOCOUNT"      : _("Event deleted in counting state because rule does not count anymore"),
  "DELAYOVER"    : _("Event opened because the delay time has elapsed before cancelling event arrived."),
  "EXPIRED"      : _("Event deleted because its livetime expired"),
  "COUNTREACHED" : _("Event deleted bacause required count had been reached"),
  "COUNTFAILED"  : _("Event created by required count was not reached in time"),
  "UPDATE"       : _("Event information updated by user"),
  "NEW"          : _("New event created"),
  "DELETE"       : _("Event deleted manually bu user"),
  "EMAIL"        : _("Email sent"),
  "SCRIPT"       : _("Script executed"),
  "CANCELLED"    : _("The event was cancelled because the corresponding OK message was received"),
}

def service_levels():
    try:
        return config.mkeventd_service_levels
    except:
        return [(0, "(no service level)")]

def action_choices(omit_hidden = False):
    # The possible actions are configured in mkeventd.mk,
    # not in multisite.mk (like the service levels). That
    # way we have not direct access to them but need
    # to load them from the configuration.
    return [ (a["id"], a["title"]) 
             for a in eventd_configuration().get("actions", []) 
             if not omit_hidden or not a.get("hidden") ]

cached_config = None
def eventd_configuration():
    global cached_config
    if cached_config and cached_config[0] is html:
        return cached_config[1]

    config = {
        "rules"                 : [],
        "debug_rules"           : False,
    }
    main_file = defaults.default_config_dir + "/mkeventd.mk"
    list_of_files = reduce(lambda a,b: a+b,
         [ [ "%s/%s" % (d, f) for f in fs if f.endswith(".mk")]
             for d, sb, fs in os.walk(defaults.default_config_dir + "/mkeventd.d" ) ], [])

    list_of_files.sort()
    for path in [ main_file ] + list_of_files:
        execfile(path, config, config)
    cached_config = (html, config)
    return config
    

def daemon_running():
    return os.path.exists(socket_path)


def send_event(event):
    # "<%PRI%>%TIMESTAMP% %HOSTNAME% %syslogtag% %msg%\n"
    prio = (event["facility"] << 3) + event["priority"]
    timestamp = time.strftime("%b %d %T", time.localtime())
    rfc = "<%d>%s %s %s: %s\n" % (
        prio, timestamp, event["host"], event["application"], event["text"])
    pipe = file(pipe_path, "w")
    pipe.write(rfc + "\n")
    return rfc

def query(query):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            timeout = config.mkeventd_connect_timeout
        except:
            timeout = 10

        sock.settimeout(timeout)
        # TODO: Pfad nicht auf OMD hart kodieren
        sock.connect(socket_path)
        sock.send(query)

        response_text = ""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return eval(response_text)
    except SyntaxError, e:
        raise MKGeneralException("Invalid response from event daemon: <pre>%s</pre>" % response_text)

    except Exception, e:
        raise MKGeneralException("Cannot connect to event daemon via %s: %s" % (socket_path, e))

def replication_mode():
    try:
        response = query("GET status")
        status = dict(zip(response[0], response[1]))
        return status["status_replication_slavemode"]
    except:
        return None


# Rule matching for simulation. Yes - there is some hateful code duplication
# here. But it does not make sense to query the live eventd here since it
# does not know anything about the currently configured but not yet activated
# rules. And also we do not want to have shared code.
def event_rule_matches(rule, event):
    if False == match(rule.get("match_host"), event["host"], complete=True):
        return _("The host name does not match.")

    if False == match(rule.get("match_application"), event["application"], complete=False):
        return _("The application (syslog tag) does not match")
    
    if "match_facility" in rule and event["facility"] != rule["match_facility"]:
        return _("The syslog facility does not match")


    # First try cancelling rules
    if "match_ok" in rule or "cancel_priority" in rule:
        if "cancel_priority" in rule:
            up, lo = rule["cancel_priority"]
            cp = event["priority"] >= lo and event["priority"] <= up
        else:
            cp = True

        match_groups = match(rule.get("match_ok", ""), event["text"], complete = False)
        if match_groups != False and cp:
            if match_groups == True:
                match_groups = ()
            return True, match_groups
            
    try:
        match_groups = match(rule.get("match"), event["text"], complete = False)
    except Exception, e:
        return _("Invalid regular expression: %s" % e)
    if match_groups == False:
        return _("The message text does not match the required pattern.")

    if "match_priority" in rule:
        prio_from, prio_to = rule["match_priority"]
        if prio_from > prio_to:
            prio_to, prio_from = prio_from, prio_to
        p = event["priority"]
        if p < prio_from or p > prio_to:
            return _("The syslog priority is not in the required range.")

    if match_groups == True:
        match_groups = () # no matching groups
    return False, match_groups

def match(pattern, text, complete = True):
    if pattern == None:
        return True
    else:
        if complete:
            if not pattern.endswith("$"):
                pattern += '$'
            m = re.compile(pattern, re.IGNORECASE).match(text)
        else:
            m = re.compile(pattern, re.IGNORECASE).search(text)
        if m:
            return m.groups()
        else:
            return False
