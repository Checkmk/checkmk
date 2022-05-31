#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.1.0p2"

# This agent plugin has been built to collect information from SAP R/3 systems
# using RFC calls. It needs the python module sapnwrfc (available in Checkmk
# git at agents/sap/sapnwrfc) and the nwrfcsdk (can be downloaded from SAP
# download portal) installed to be working. You can configure the agent plugin
# using the configuration file /etc/check_mk/sap.cfg (a sample file can be
# found in Checkmk git at agents/sap/sap.cfg) to tell it how to connect to
# your SAP instance and which values you want to fetch from your system to be
# forwarded to and checked by Checkmk.
#
# This current agent has been developed and tested with:
#   python-sapnwrfc-0.19
#
# During development the "CCMS_Doku.pdf" was really helpful.

#   #################################
#   #                               #
#   #         N  O  T  E            #
#   #                               #
#   #################################
#
# This plugin will only work with python2 as sapnwrfc is not available
# for python 3.
# This plugin will be converted to python2 automatically, and a patch in
# the bakery plugin will make sure only the python 2 version will be deployed
# -- such that even on monitored hosts that provide both py3 and py2 the
# py2 variant is executed.
#
# Make sure to remove said patch if the plugin is python 2/3 compatible!
#

import ast
import datetime
import fcntl
import fnmatch
import os
import sys
import time

try:
    from typing import Any, Dict, List, Tuple, Union
except ImportError:
    pass

# sapnwrfc needs to know where the libs are located. During
# development the import failed, since the module did not
# find the libraries. So we preload the library to have it
# already loaded.
try:
    import sapnwrfc  # type: ignore[import]
except ImportError as e:
    if "sapnwrfc.so" in str(e):
        sys.stderr.write(
            "Unable to find the library sapnwrfc.so. Maybe you need to put a file pointing to\n"
            "the sapnwrfc library directory into the /etc/ld.so.conf.d directory. For example\n"
            "create the file /etc/ld.so.conf.d/sapnwrfc.conf containing the path\n"
            '"/usr/sap/nwrfcsdk/lib" and run "ldconfig" afterwards.\n'
        )
        sys.exit(1)
    elif "No module named sapnwrfc" in str(e):
        sys.stderr.write("Missing the Python module sapnwfrc.\n")
        sys.exit(1)
    else:
        raise

# #############################################################################

# This sign is used to separate the path parts given in the config
SEPARATOR = "/"

# This are the different classes of monitoring objects which
# can be found in the tree.
#
# Summarizs information from several subnodes
MTE_SUMMARY = "050"
# A monitoring object which has several subnodes which lead to the status
# of this object. For example it is the "CPU" object on a host
MTE_MON_OBJ = "070"
# Contains performance information (which can be used to create graphs from)
MTE_PERFORMANCE = "100"
# Might contain several messages
MTE_MSG_CONTAINER = "101"
# Contains a single status message
MTE_SINGLE_MSG = "102"
# This is a long text label without status
MTE_LONG_TXT = "110"
# This is a short text label without status
MTE_SHORT_TXT = "111"
# Is a "folder" which has no own state, just computed by its childs
MTE_VIRTUAL = "199"

# This map converts between the SAP color codes (key values) and the
# nagios state codes and strings
STATE_VALUE_MAP = {
    0: (0, "OK"),  # GRAY  (inactive or no current info available) -> OK
    1: (0, "OK"),  # GREEN  -> OK
    2: (1, "WARN"),  # YELLOW -> WARNING
    3: (2, "CRIT"),  # RED    -> CRITICAL
}

STATE_LOGWATCH_MAP = ["O", "O", "W", "C"]

# Monitoring objects of these classes are skipped during processing
SKIP_MTCLASSES = [
    MTE_VIRTUAL,
    MTE_SUMMARY,
    MTE_MON_OBJ,
    MTE_SHORT_TXT,
    MTE_LONG_TXT,
]

MK_CONFDIR = os.getenv("MK_CONFDIR") or "/etc/check_mk"
MK_VARDIR = os.getenv("MK_VARDIR") or "/var/lib/check_mk_agent"

STATE_FILE = MK_VARDIR + "/sap.state"
state_file_changed = False

# #############################################################################

# Settings to be used to connect to the SAP R/3 host.
local_cfg = {
    "ashost": "localhost",
    "sysnr": "00",
    "client": "100",
    "user": "",
    "passwd": "",
    "trace": "3",
    "loglevel": "warn",
    #'lang':     'EN',
    #'host_prefix': 'FOOBAR_',
}

# A list of strings, while the string must match the full path to one or
# several monitor objects. We use unix shell patterns during matching, so
# you can use several chars as placeholders:
#
# *      matches everything
# ?      matches any single character
# [seq]  matches any character in seq
# [!seq] matches any character not in seq
#
# The * matches the whole following string and does not end on next "/".
# For examples, take a look at the default config file (/etc/check_mk/sap.cfg).
monitor_paths = [
    "SAP CCMS Monitor Templates/Dialog Overview/*",
]
monitor_types = []  # type: List[str]
config_file = MK_CONFDIR + "/sap.cfg"

cfg = {}  # type: Union[List[Dict[Any, Any]], Dict[Any, Any]]
if os.path.exists(config_file):
    with open(config_file) as opened_file:
        exec(opened_file.read())
    if isinstance(cfg, dict):
        cfg = [cfg]
else:
    cfg = [local_cfg]

# Load the state file into memory
try:
    with open(STATE_FILE) as opened_file:
        states = ast.literal_eval(opened_file.read())
except IOError:
    states = {}

# index of all logfiles which have been found in a run. This is used to
# remove logfiles which are not available anymore from the states dict.
logfiles = []
conn = None

# #############################################################################

#
# HELPERS
#


def to_be_monitored(path, toplevel_match=False):
    for rule in monitor_paths:
        if toplevel_match and rule.count("/") > 1:
            rule = "/".join(rule.split("/")[:2])

        if fnmatch.fnmatch(path, rule):
            return True
    return False


def node_path(tree, node, path=""):
    if path:
        path = node["MTNAMESHRT"].rstrip() + SEPARATOR + path
    else:
        path = node["MTNAMESHRT"].rstrip()

    if node["ALPARINTRE"] > 0:
        parent_node = tree[node["ALPARINTRE"] - 1]
        return node_path(tree, parent_node, path)
    return path


#
# API ACCESS FUNCTIONS
#


def query(what, params, debug=False):
    if conn:
        fd = conn.discover(what)

    if debug:
        sys.stdout.write("Name: %s Params: %s\n" % (fd.name, fd.handle.parameters))
        sys.stdout.write("Given-Params: %s\n" % params)

    f = fd.create_function_call()
    for param_key, val in params.items():
        getattr(f, param_key)(val)
    f.invoke()

    ret = f.RETURN.value
    if ret["TYPE"] == "E":
        sys.stderr.write("ERROR: %s\n" % ret["MESSAGE"].strip())

    return f


def login():
    f = query(
        "BAPI_XMI_LOGON",
        {
            "EXTCOMPANY": "Mathias Kettner GmbH",
            "EXTPRODUCT": "Check_MK SAP Agent",
            "INTERFACE": "XAL",
            "VERSION": "1.0",
        },
    )
    # sys.stdout.write("%s\n" % f.RETURN)
    return f.SESSIONID.value


def logout():
    query(
        "BAPI_XMI_LOGOFF",
        {
            "INTERFACE": "XAL",
        },
    )


def mon_list(cfg_entry):
    f = query(
        "BAPI_SYSTEM_MON_GETLIST",
        {
            "EXTERNAL_USER_NAME": cfg_entry["user"],
        },
    )
    l = []
    for mon in f.MONITOR_NAMES.value:
        l.append((mon["MS_NAME"].rstrip(), mon["MONI_NAME"].rstrip()))
    return l


# def ms_list( cfg ):
#    f = query("BAPI_SYSTEM_MS_GETLIST", {
#        'EXTERNAL_USER_NAME': cfg['user'],
#    })
#    l = []
#    for ms in f.MONITOR_SETS.value:
#        l.append(ms['NAME'].rstrip())
#    return l


def mon_tree(cfg_entry, ms_name, mon_name):
    f = query(
        "BAPI_SYSTEM_MON_GETTREE",
        {
            "EXTERNAL_USER_NAME": cfg_entry["user"],
            "MONITOR_NAME": {"MS_NAME": ms_name, "MONI_NAME": mon_name},
        },
    )
    tree = f.TREE_NODES.value
    for node in tree:
        node["PATH"] = ms_name + SEPARATOR + node_path(tree, node)
    return tree


def tid(node):
    return {
        "MTSYSID": node["MTSYSID"].strip(),
        "MTMCNAME": node["MTMCNAME"].strip(),
        "MTNUMRANGE": node["MTNUMRANGE"].strip(),
        "MTUID": node["MTUID"].strip(),
        "MTCLASS": node["MTCLASS"].strip(),
        "MTINDEX": node["MTINDEX"].strip(),
        "EXTINDEX": node["EXTINDEX"].strip(),
    }


def mon_perfdata(cfg_entry, node):
    f = query(
        "BAPI_SYSTEM_MTE_GETPERFCURVAL",
        {
            "EXTERNAL_USER_NAME": cfg_entry["user"],
            "TID": tid(node),
        },
    )
    value = f.CURRENT_VALUE.value["LASTPERVAL"]

    f = query(
        "BAPI_SYSTEM_MTE_GETPERFPROP",
        {
            "EXTERNAL_USER_NAME": cfg_entry["user"],
            "TID": tid(node),
        },
    )
    if f.PROPERTIES.value["DECIMALS"] != 0:
        value = (value + 0.0) / 10 ** f.PROPERTIES.value["DECIMALS"]
    uom = f.PROPERTIES.value["VALUNIT"].strip()

    return value, uom


def mon_msg(cfg_entry, node):
    f = query(
        "BAPI_SYSTEM_MTE_GETSMVALUE",
        {
            "EXTERNAL_USER_NAME": cfg_entry["user"],
            "TID": tid(node),
        },
    )
    data = f.VALUE.value
    dt = parse_dt(data["SMSGDATE"], data["SMSGTIME"])
    return (dt, data["MSG"].strip())


def parse_dt(d, t):
    d = d.strip()
    t = t.strip()
    if not d or not t:
        return None
    return datetime.datetime(*time.strptime(d + t, "%Y%m%d%H%M%S")[:6])


def mon_alerts(cfg_entry, node):
    f = query(
        "BAPI_SYSTEM_MTE_GETALERTS",
        {
            "EXTERNAL_USER_NAME": cfg_entry["user"],
            "TID": tid(node),
        },
    )
    return f.ALERTS.value


def aid(alert):
    return {
        "ALSYSID": alert["ALSYSID"],
        "MSEGNAME": alert["MSEGNAME"],
        "ALUNIQNUM": alert["ALUNIQNUM"],
        "ALINDEX": alert["ALINDEX"],
        "ALERTDATE": alert["ALERTDATE"],
        "ALERTTIME": alert["ALERTTIME"],
    }


def alert_details(cfg_entry, alert):
    f = query(
        "BAPI_SYSTEM_ALERT_GETDETAILS",
        {
            "EXTERNAL_USER_NAME": cfg_entry["user"],
            "AID": aid(alert),
        },
    )
    # prop  = f.PROPERTIES.value
    state = f.VALUE.value
    msg = f.XMI_EXT_MSG.value["MSG"].strip()
    return state, msg


def process_alerts(cfg_entry, logs, ms_name, mon_name, node, alerts):
    global state_file_changed

    sid = node["MTSYSID"].strip() or "Other"
    context = node["MTMCNAME"].strip() or "Other"
    path = node["PATH"]

    # Use the sid as hostname for the logs
    hostname = sid
    logfile = context + "/" + path

    logfiles.append((hostname, logfile))

    logs.setdefault(sid, {})
    logs[hostname][logfile] = []
    newest_log_dt = None
    for alert in alerts:
        dt = parse_dt(alert["ALERTDATE"], alert["ALERTTIME"])

        if (hostname, logfile) in states and states[(hostname, logfile)] >= dt:
            continue  # skip log messages which are older than the last cached date

        if not newest_log_dt or dt > newest_log_dt:
            newest_log_dt = dt  # store the newest log of this run

        alert_state, alert_msg = alert_details(cfg_entry, alert)
        # Format lines to "logwatch" format
        logs[hostname][logfile].append(
            "%s %s %s"
            % (
                STATE_LOGWATCH_MAP[alert_state["VALUE"]],
                dt.strftime("%Y-%m-%d %H:%M:%S"),
                alert_msg,
            )
        )

    if newest_log_dt:
        # Write newest log age to cache to prevent double processing of logs
        states[(hostname, logfile)] = newest_log_dt
        state_file_changed = True
    return logs


def check(cfg_entry):
    global conn
    conn = sapnwrfc.base.rfc_connect(cfg_entry)
    login()

    logs = {}  # type: Dict[str, Dict[str, List]]
    sap_data = {}  # type: Dict[str, List]

    # This loop is used to collect all information from SAP
    for ms_name, mon_name in mon_list(cfg_entry):
        path = ms_name + SEPARATOR + mon_name
        if not to_be_monitored(path, True):
            continue

        tree = mon_tree(cfg_entry, ms_name, mon_name)
        for node in tree:
            if not to_be_monitored(node["PATH"]):
                continue
            # sys.stdout.write("%s\n" % node["PATH"])

            status_details = ""  # type: Union[str, Tuple[str, Any]]
            perfvalue = "-"
            uom = "-"

            # Use precalculated states
            state = {
                "VALUE": node["ACTUALVAL"],
                "SEVERITY": node["ACTUALSEV"],
            }

            if state["VALUE"] not in STATE_VALUE_MAP:
                sys.stdout.write("UNHANDLED STATE VALUE\n")
                sys.exit(1)

            #
            # Handle different object classes individually
            # to get details about them
            #

            if monitor_types and node["MTCLASS"] not in monitor_types:
                continue  # Skip unwanted classes if class filtering is enabled

            if node["MTCLASS"] == MTE_PERFORMANCE:
                perfvalue, this_uom = mon_perfdata(cfg_entry, node)
                uom = this_uom if this_uom else uom

            elif node["MTCLASS"] == MTE_SINGLE_MSG:
                status_details = "%s: %s" % mon_msg(cfg_entry, node)

            elif node["MTCLASS"] == MTE_MSG_CONTAINER:

                alerts = mon_alerts(cfg_entry, node)
                logs = process_alerts(cfg_entry, logs, ms_name, mon_name, node, alerts)
                if len(alerts) > 0:
                    last_alert = alerts[-1]
                    dt = parse_dt(last_alert["ALERTDATE"], last_alert["ALERTTIME"])
                    alert_state, alert_msg = alert_details(cfg_entry, last_alert)
                    last_msg = "%s: %s - %s" % (
                        dt,
                        STATE_VALUE_MAP[alert_state["VALUE"]][1],
                        alert_msg,
                    )

                    status_details = "%d Messages, Last: %s" % (len(alerts), last_msg)
                else:
                    status_details = "The log is empty"

            elif node["MTCLASS"] not in SKIP_MTCLASSES:
                # Add an error to output on unhandled classes
                status_details = "UNHANDLED MTCLASS", node["MTCLASS"]

            if node["MTCLASS"] not in SKIP_MTCLASSES:
                sid = node["MTSYSID"].strip() or "Other"
                context = node["MTMCNAME"].strip() or "Other"
                path = node["PATH"]

                sap_data.setdefault(sid, [])
                sap_data[sid].append(
                    "%s\t%d\t%3d\t%s\t%s\t%s\t%s"
                    % (
                        context,
                        state["VALUE"],
                        state["SEVERITY"],
                        path,
                        perfvalue,
                        uom,
                        status_details,
                    )
                )

    for host, host_sap in sap_data.items():
        sys.stdout.write("<<<<%s%s>>>>\n" % (cfg_entry.get("host_prefix", ""), host))
        sys.stdout.write("<<<sap:sep(9)>>>\n")
        sys.stdout.write("%s\n" % "\n".join(host_sap))
    sys.stdout.write("<<<<>>>>\n")

    for host, host_logs in logs.items():
        sys.stdout.write("<<<<%s>>>>\n" % host)
        sys.stdout.write("<<<logwatch>>>\n")
        for log, lines in host_logs.items():
            sys.stdout.write("[[[%s]]]\n" % log)
            if lines:
                sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.write("<<<<>>>>\n")

    logout()
    conn.close()


# It is possible to configure multiple SAP instances to monitor. Loop them all, but
# do not terminate when one connection failed
processed_all = True
try:
    for entry in cfg:
        try:
            check(entry)
            sys.stdout.write("<<<sap_state:sep(9)>>>\n%s\tOK\n" % entry["ashost"])
        except sapnwrfc.RFCCommunicationError as e:
            sys.stderr.write("ERROR: Unable to connect (%s)\n" % e)
            sys.stdout.write(
                "<<<sap_state:sep(9)>>>\n%s\tUnable to connect (%s)\n" % (entry["ashost"], e)
            )
            processed_all = False
        except Exception as e:
            sys.stderr.write("ERROR: Unhandled exception (%s)\n" % e)
            sys.stdout.write(
                "<<<sap_state:sep(9)>>>\n%s\tUnhandled exception (%s)\n" % (entry["ashost"], e)
            )
            processed_all = False

    # Now check whether or not an old logfile needs to be removed. This can only
    # be done this way, when all hosts have been reached. Otherwise the cleanup
    # is skipped.
    if processed_all:
        for key in states.keys():
            if key not in logfiles:
                state_file_changed = True
                del states[key]

    # Only write the state file once per run. And only when it has been changed
    if state_file_changed:
        new_file = STATE_FILE + ".new"
        state_fd = os.open(new_file, os.O_WRONLY | os.O_CREAT)
        fcntl.flock(state_fd, fcntl.LOCK_EX)
        os.write(state_fd, repr(states).encode("utf-8"))
        os.close(state_fd)
        os.rename(STATE_FILE + ".new", STATE_FILE)

except Exception as e:
    sys.stderr.write("ERROR: Unhandled exception (%s)\n" % e)

sys.exit(0)
