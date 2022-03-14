#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# 2019-01-17, comNET GmbH, Fabian Binder
"""
Special agent for monitoring Zerto application with Check_MK.
"""

import argparse
import json
import logging
import sys

import requests

from cmk.utils.exceptions import MKException

LOGGER = logging.getLogger(__name__)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)

    # flags
    parser.add_argument(
        "-a", "--authentication", default="windows", type=str, help="Authentication method"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Debug mode: raise Python exceptions"
    )
    parser.add_argument("-v", "--verbose", action="count", help="Be more verbose")
    parser.add_argument("-u", "--username", required=True, help="Zerto user name")
    parser.add_argument("-p", "--password", required=True, help="Zerto user password")
    parser.add_argument("hostaddress", help="Zerto host name")

    args = parser.parse_args(argv)

    if args.verbose and args.verbose >= 2:
        fmt = "%(levelname)s: %(name)s: %(filename)s: %(lineno)s %(message)s"
        lvl = logging.DEBUG
    elif args.verbose:
        fmt = "%(levelname)s: %(message)s"
        lvl = logging.INFO
    else:
        fmt = "%(levelname)s: %(message)s"
        lvl = logging.WARNING
    logging.basicConfig(level=lvl, format=fmt)

    return args


class ZertoRequest:
    def __init__(self, connection_url, session_id):
        self._endpoint = "%s/vms" % connection_url
        self._headers = {"x-zerto-session": session_id, "content-type": "application/json"}

    def get_vms_data(self):
        response = requests.get(self._endpoint, headers=self._headers, verify=False)  # nosec

        if response.status_code != 200:
            LOGGER.debug("response status code: %s", response.status_code)
            raise RuntimeError("Call to ZVM failed")
        try:
            data = json.loads(response.text)
        except ValueError:
            raise ValueError("Got invalid data from host")
        return data


class ZertoConnection:
    def __init__(self, hostaddress, username, password):
        self._credentials = username, password
        self._host = hostaddress
        self.base_url = "https://%s:9669/v1" % self._host

    def get_session_id(self, authentication):
        url = "%s/session/add" % self.base_url
        if authentication == "windows":
            response = requests.post(url, auth=self._credentials, verify=False)  # nosec
        else:
            dataval = {"AuthenticationMethod": 1}
            LOGGER.debug("VCenter dataval: %r", dataval)
            headers = {"content-type": "application/json"}
            response = requests.post(  # nosec
                url, data=dataval, auth=self._credentials, headers=headers, verify=False
            )

        LOGGER.debug("Response status code: %s", response.status_code)

        if response.status_code != 200:
            raise AuthError("Failed authenticating to the Zerto Virtual Manager")

        return response.headers.get("x-zerto-session")


class AuthError(MKException):
    pass


def main(argv=None):
    args = parse_arguments(argv or sys.argv[1:])
    connection = ZertoConnection(args.hostaddress, args.username, args.password)
    session_id = connection.get_session_id(args.authentication)
    request = ZertoRequest(connection.base_url, session_id)
    vm_data = request.get_vms_data()

    for vm in vm_data:
        try:
            sys.stdout.write("<<<<{}>>>>\n".format(vm["VmName"]))
            sys.stdout.write("<<<zerto_vpg_rpo:sep(124)>>>\n")
            sys.stdout.write("{}|{}|{}\n".format(vm["VpgName"], vm["Status"], vm["ActualRPO"]))
            sys.stdout.write("<<<<>>>>\n")
        except KeyError:
            continue
