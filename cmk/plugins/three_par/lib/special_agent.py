#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring 3par devices.
"""

import argparse
import json
import sys

import requests
import urllib3

import cmk.utils.password_store

from cmk.rulesets.v1 import Title

DEFAULT_VALUES = {
    "system": Title("System: Storage Array Configuration"),
    "cpgs": Title("Common Provisioning Groups: Virtual pool configuration"),
    "volumes": Title("Volumes: Virtual Volume Summary"),
    "hosts": Title("Hosts: Host Capacity & Utilization"),
    "capacity": Title("Capacity: Array Capacity & Utilization"),
    "ports": Title("Ports: Port Utilization (FC and iSCSI)"),
    "remotecopy": Title("RemoteCopy: Remote Copy Configuration"),
}


VALID_VALUES = {
    **DEFAULT_VALUES,
    "hostsets": Title("HostSets: Host Set Configuration"),
    "volumesets": Title("VolumeSets: Volume Set Configuration"),
    "vluns": Title("VLUNs: Virtual LUN Configuration"),
    "flashcache": Title("FlashCache: Flash Cache Configuration"),
    "users": Title("Users: User Management"),
    "roles": Title("Roles: Role Management"),
    "qos": Title("QoS: Quality of Service Configuration"),
}


def _get_values_list(opt_string):
    values = opt_string.split(",")
    invalid_choices = set(values) - set(VALID_VALUES)
    if invalid_choices:
        raise ValueError("invalid values: %r" % invalid_choices)
    return values


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-u", "--user", required=True, help="Username for 3par login")
    parser.add_argument("-p", "--password", required=True, help="Password for 3par login")
    parser.add_argument("-P", "--port", required=True, help="Port for connection to 3par")
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="Disable verification of the servers ssl certificate",
    )
    parser.add_argument(
        "-v",
        "--values",
        required=True,
        type=_get_values_list,
        help=f"Comma separated list of values to fetch from 3par system. Choose from: {', '.join(VALID_VALUES)}",
    )
    parser.add_argument("host", help="Host name or IP address of 3par system")
    args = parser.parse_args(argv)
    return args


def main(argv=None):
    if argv is None:
        cmk.utils.password_store.replace_passwords()
        argv = sys.argv[1:]
    args = parse_arguments(argv)

    url = f"https://{args.host}:{args.port}/api/v1"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if args.no_cert_check:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Initiate connection and get session Key. The api expects the login data
    # in json format. The standard port for all requests is 8080 as it is hard
    # coded above. Maybe this will be changed later!
    try:
        req = requests.post(
            "%s/credentials" % url,
            json={"user": args.user, "password": args.password},
            headers=headers,
            timeout=10,
            verify=not args.no_cert_check,
        )

    except requests.exceptions.RequestException as e:
        sys.stderr.write("Error: %s\n" % e)
        return 1

    # Status code should be 201.
    if not req.status_code == requests.codes.CREATED:
        sys.stderr.write(
            f"Wrong status code: {req.status_code}. Expected: {requests.codes.CREATED} \n"
        )
        return 1
    try:
        # As Response we get the key also in json format. We just need the
        # key in our header for all further requests on the api.
        data = json.loads(req.text)
        headers["X-HP3PAR-WSAPI-SessionKey"] = data["key"]
    except Exception:
        raise Exception("No session key received")

    # Get the requested data. We put every needed value into an extra section
    # to get better performance in the checkplugin if less data is needed.

    for value in args.values:
        sys.stdout.write("<<<3par_%s:sep(0)>>>\n" % value)
        req = requests.get(
            f"{url}/{value}", headers=headers, timeout=10, verify=not args.no_cert_check
        )
        value_data = req.text.replace("\r\n", "").replace("\n", "").replace(" ", "")
        sys.stdout.write(value_data + "\n")

    # Perform a proper disconnect. The Connection is closed if the session key
    # is deleted. The standard timeout for a session would be 15 minutes.
    req = requests.delete(
        "{}/credentials/{}".format(url, headers["X-HP3PAR-WSAPI-SessionKey"]),
        headers=headers,
        timeout=10,
        verify=not args.no_cert_check,
    )

    if not req.status_code == requests.codes.OK:
        sys.stderr.write(f"Wrong status code: {req.status_code}. Expected: {requests.codes.OK} \n")
        return 1
    return None
