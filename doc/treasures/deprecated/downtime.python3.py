#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  type: ignore
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Sets/Removes downtimes via Checkmk Multisite Webservice
# Before you can use this script, please read:
# http://mathias-kettner.de/checkmk_multisite_automation.html
# And create an automation user - best with the name 'automation'
# And make sure that this user either has the admin role or is
# contact for all relevant objects.

# Restrictions / Bugs
# - When removing host downtimes, always *all* services downtimes
#   are also removed
# - When removing service downtimes the service names are interpreted
#   as regular expressions, but not when setting
# -> We need a specialized view for the downtimes. Or even better
#    implement the "Remove all downtimes" button in a normal hosts/
#    services views.

import getopt
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

omd_site = os.getenv("OMD_SITE")
omd_root = os.getenv("OMD_ROOT")


def bail_out(reason):
    sys.stderr.write(reason + "\n")
    sys.exit(1)


def verbose(text):
    if opt_verbose:
        sys.stdout.write(text + "\n")


def usage():
    sys.stdout.write(
        """Usage: downtime [-r] [OPTIONS] HOST [SERVICE1] [SERVICE2...]
This program sets and removes downtimes on hosts and services
via command line. If you run this script from within an OMD
site then most options will be guessed automatically. Currently
the script only supports cookie based login - no HTTP basic
authentication.
Before you use this script, please read:
http://mathias-kettner.de/checkmk_multisite_automation.html
You need to create an automation user - best with the name 'automation'
- and make sure that this user either has the admin role or is contact
for all relevant objects.
Options:
  -v, --verbose    Show what's going on (specify twice for more verbose output)
  -s, --set        Set downtime (this is the default and thus optional)
  -r, --remove     Remove all downtimes from that host/service
  -c, --comment    Comment for the downtime (otherwise "Automatic downtime")
  -d, --duration   Duration of the downtime in minutes (default: 120)
  -h, --help       Show this help and exit
  -u, --user       Name of automation user (default: "automation")
  -S, --secret     Automation secret (default: read from user settings)
  -U, --url        Base-URL of Multisite (default: guess local OMD site)
  -a, --all        Include all services when setting/removing host downtime
"""
    )


short_options = "vhrsc:d:u:S:aU:"
long_options = [
    "verbose",
    "help",
    "set",
    "remove",
    "comment=",
    "url=",
    "duration=",
    "user=",
    "secret=",
    "all",
]

opt_all = False
opt_verbose = 0
opt_mode = "set"
opt_comment = "Automatic downtime"
opt_user = "automation"
opt_secret = None
opt_url = None
opt_duration = 120

if omd_site:
    opt_url = "http://localhost/" + omd_site + "/check_mk/"
try:
    opts, args = getopt.getopt(sys.argv[1:], short_options, long_options)
except getopt.GetoptError as err:
    sys.stderr.write("%s\n\n" % err)
    usage()
    sys.exit(1)

for o, a in opts:
    # Docu modes
    if o in ["-h", "--help"]:
        usage()
        sys.exit(0)

    # Modifiers
    elif o in ["-v", "--verbose"]:
        opt_verbose += 1
    elif o in ["-a", "--all"]:
        opt_all = True
    elif o in ["-s", "--set"]:
        opt_mode = "set"
    elif o in ["-r", "--remove"]:
        opt_mode = "remove"
    elif o in ["-c", "--comment"]:
        opt_comment = a
    elif o in ["-d", "--duration"]:
        opt_duration = int(a)
    elif o in ["-u", "--user"]:
        opt_user = a
    elif o in ["-S", "--secret"]:
        opt_secret = a
    elif o in ["-U", "--url"]:
        opt_url = a

if omd_site and not opt_secret:
    try:
        opt_secret = (
            open(omd_root + "/var/check_mk/web/" + opt_user + "/automation.secret").read().strip()
        )
    except Exception as e:
        bail_out("Cannot read automation secret from user %s: %s" % (opt_user, e))

elif not omd_site and not opt_secret:
    bail_out("Please specify the automation secret for the user '%s'!" % opt_user)

if not opt_url:
    bail_out("Please specify the URL to Check_MK Multisite with -U.")

if not opt_url.endswith("/check_mk/"):
    bail_out("The automation URL must end with /check_mk/")

if not args:
    bail_out("Please specify the host to set a downtime for.")

arg_host = args[0]
arg_services = args[1:]

if opt_mode == "set":
    verbose("Mode:          set downtime")
    verbose("Duration:      %dm" % opt_duration)
else:
    verbose("Mode:          remove downtimes")
verbose("Host:          " + arg_host)
if arg_services:
    verbose("Services:      " + " ".join(arg_services))
verbose("Multisite-URL: " + opt_url)
verbose("User:          " + opt_user)
verbose("Secret:        " + (opt_secret or "(none specified)"))


def make_url(base, variables):
    vartext = "&".join(
        ["%s=%s" % (varname, urllib.parse.quote(value)) for (varname, value) in variables]
    )
    return base + "?" + vartext


def set_downtime(variables, add_vars):
    url = make_url(opt_url + "view.py", variables + add_vars)
    verbose("URL:           " + url)
    try:
        pipe = urllib.request.urlopen(url)
        lines = pipe.readlines()
        verbose(" --> Got %d lines of response" % len(lines))
        if opt_verbose > 1:
            for line in lines:
                verbose("OUTPUT: %s" % line.rstrip())
        for line in lines:
            if line.startswith(b"<div class=error>"):
                bail_out(line[17:].split("<")[0])
    except Exception as e:
        bail_out("Cannot call Multisite URL: %s" % e)


# We have 6 different modes:
# Only the host           | 1: set | 4: remove
# Only specific services  | 2: set | 5: remove
# Host and all services   | 3: set | 6: remove

# Authentication and host selection
variables = [
    ("_username", opt_user),
    ("_secret", opt_secret),
    ("_transid", "-1"),
    ("_do_confirm", "yes"),
    ("_do_actions", "yes"),
    ("host", arg_host),
]

# Action variables for setting or removing (works in all views)
if opt_mode == "remove":
    variables += [
        ("_remove_downtimes", "Remove"),
        ("_down_remove", "Remove"),
    ]
else:
    variables += [
        ("_down_from_now", "yes"),
        ("_down_minutes", str(opt_duration)),
        ("_down_comment", opt_comment),
    ]

# Downtime on host (handles 1 & 4, needed for 3 & 6)
if not arg_services:
    set_downtime(variables, [("view_name", "hoststatus")])

# Downtime on specific services (handles 2 & 5)
else:
    variables.append(("_do_confirm_service_downtime", "yes"))
    for service in arg_services:
        set_downtime(variables, [("view_name", "service"), ("service", service)])

# Handle services for option --all (3 & 6)
if opt_all:
    set_downtime(variables, [("view_name", "host")])
