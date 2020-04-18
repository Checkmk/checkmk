#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import print_function
import getopt
import json
import sys

import requests
import urllib3  # type: ignore[import]

import cmk.utils.password_store

#   .--Arguments-----------------------------------------------------------.
#   |           _                                         _                |
#   |          / \   _ __ __ _ _   _ _ __ ___   ___ _ __ | |_ ___          |
#   |         / _ \ | '__/ _` | | | | '_ ` _ \ / _ \ '_ \| __/ __|         |
#   |        / ___ \| | | (_| | |_| | | | | | |  __/ | | | |_\__ \         |
#   |       /_/   \_\_|  \__, |\__,_|_| |_| |_|\___|_| |_|\__|___/         |
#   |                    |___/                                             |
#   '----------------------------------------------------------------------'


def usage():
    sys.stderr.write("""Check_MK 3par Agent
USAGE: agent_3par [OPTIONS] HOST
       agent_3par -h

ARGUMENTS:
  HOST                                      Host name or IP address of 3par system

OPTIONS:
  -h, --help                                Show this help message and exit
  -u USER, --user USER                      Username for 3par login
  -p PASSWORD, --password PASSWORD          Password for 3par login
  --verify-certs yes/no                     Enable/disable verification of the servers
                                            ssl certificate. Disabled by default.
  -v VALUE,VALUE, --values VALUE,VALUE      Values to fetch from 3par system.
                                            Possible values:    system
                                                                hosts
                                                                ports
                                                                flashcache
                                                                volumes
                                                                cpgs
""")


#.


def main(sys_argv=None):
    if sys_argv is None:
        cmk.utils.password_store.replace_passwords()
        sys_argv = sys.argv[1:]

    opt_host = None
    opt_user = None
    opt_password = None
    opt_values = ["system", "cpgs", "volumes", "hosts", "capacity", "ports", "remotecopy"]
    opt_verify = False

    short_options = "hh:u:p:v:"
    long_options = ["help", "user=", "password=", "values=", "verify-certs="]

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    for opt, arg in opts:
        if opt in ['-h', '--help']:
            usage()
            sys.exit(0)
        elif opt in ["-u", "--user"]:
            opt_user = arg
        elif opt in ["-p", "--password"]:
            opt_password = arg
        elif opt in ["-v", "--values"]:
            opt_values = arg.split(",")
        elif opt in ['--verify-certs']:
            opt_verify = arg == "yes"
        elif not opt:
            usage()
            sys.exit(0)

    if len(args) == 1:
        opt_host = args[0]
    elif not args:
        sys.stderr.write("ERROR: No host given.\n")
        return 1
    else:
        sys.stderr.write("ERROR: Please specify exactly one host.\n")
        return 1
    #.-

    url = "https://%s:8080/api/v1" % opt_host
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if not opt_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Initiate connection and get session Key. The api expects the login data
    # in json format. The standard port for all requests is 8080 as it is hard
    # coded above. Maybe this will be changed later!
    try:
        req = requests.post("%s/credentials" % url,
                            json={
                                'user': opt_user,
                                'password': opt_password
                            },
                            headers=headers,
                            timeout=10,
                            verify=opt_verify)

    except requests.exceptions.RequestException as e:
        sys.stderr.write("Error: %s\n" % e)
        return 1

    # Status code should be 201.
    if not req.status_code == requests.codes.CREATED:
        sys.stderr.write("Wrong status code: %s. Expected: %s \n" %
                         (req.status_code, requests.codes.CREATED))
        return 1
    else:
        try:
            # As Response we get the key also in json format. We just need the
            # key in our header for all further requests on the api.
            data = json.loads(req.text)
            headers["X-HP3PAR-WSAPI-SessionKey"] = data["key"]
        except Exception:
            raise Exception("No session key received")

    # Get the requested data. We put every needed value into an extra section
    # to get better performance in the checkplugin if less data is needed.

    for value in opt_values:
        print("<<<3par_%s:sep(0)>>>" % value)
        req = requests.get("%s/%s" % (url, value), headers=headers, timeout=10, verify=opt_verify)
        value_data = req.text.replace("\r\n", "").replace("\n", "").replace(" ", "")
        print(value_data)

    # Perform a proper disconnect. The Connection is closed if the session key
    # is deleted. The standard timeout for a session would be 15 minutes.
    req = requests.delete("%s/credentials/%s" % (url, headers["X-HP3PAR-WSAPI-SessionKey"]),
                          headers=headers,
                          timeout=10,
                          verify=opt_verify)

    if not req.status_code == requests.codes.OK:
        sys.stderr.write("Wrong status code: %s. Expected: %s \n" %
                         (req.status_code, requests.codes.OK))
        return 1
