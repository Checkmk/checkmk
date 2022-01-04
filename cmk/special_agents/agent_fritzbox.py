#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This agent uses UPNP API calls to the Fritz!Box to gather information
# about connection configuration and status.

# UPNP API CALLS THAT HAVE BEEN PROVEN WORKING
# Tested on:
# - AVM FRITZ!Box Fon WLAN 7360 111.05.51
# General Device Infos:
# http://fritz.box:49000/igddesc.xml
#
# http://fritz.box:49000/igdconnSCPD.xml
# get_upnp_info('WANIPConn1', 'urn:schemas-upnp-org:service:WANIPConnection:1', 'GetStatusInfo')
# get_upnp_info('WANIPConn1', 'urn:schemas-upnp-org:service:WANIPConnection:1', 'GetExternalIPAddress')
# get_upnp_info('WANIPConn1', 'urn:schemas-upnp-org:service:WANIPConnection:1', 'GetConnectionTypeInfo')
# get_upnp_info('WANIPConn1', 'urn:schemas-upnp-org:service:WANIPConnection:1', 'GetNATRSIPStatus')
#
# http://fritz.box:49000/igdicfgSCPD.xml
# get_upnp_info('WANCommonIFC1', 'urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1', 'GetAddonInfos')
# get_upnp_info('WANCommonIFC1', 'urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1', 'GetCommonLinkProperties')
#
# http://fritz.box:49000/igddslSCPD.xml
# get_upnp_info('WANDSLLinkC1', 'urn:schemas-upnp-org:service:WANDSLLinkConfig:1', 'GetDSLLinkInfo')
"""Checkmk special agent Fritz!Box"""

import argparse
import logging
import pprint
import re
import sys
import traceback
from typing import Final, Mapping

import requests

from cmk.special_agents.utils import vcrtrace

_QUERIES: Final = (
    ("WANIPConn1", "urn:schemas-upnp-org:service:WANIPConnection:1", "GetStatusInfo"),
    (
        "WANIPConn1",
        "urn:schemas-upnp-org:service:WANIPConnection:1",
        "GetExternalIPAddress",
    ),
    (
        "WANCommonIFC1",
        "urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1",
        "GetAddonInfos",
    ),
    (
        "WANCommonIFC1",
        "urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1",
        "GetCommonLinkProperties",
    ),
    ("WANDSLLinkC1", "urn:schemas-upnp-org:service:WANDSLLinkConfig:1", "GetDSLLinkInfo"),
)

_SOAP_TEMPLATE = """
<?xml version='1.0' encoding='utf-8'?>
  <s:Envelope
   s:encodingStyle='http://schemas.xmlsoap.org/soap/encoding/'
   xmlns:s='http://schemas.xmlsoap.org/soap/envelope/'>
    <s:Body>
        <u:%s xmlns:u="%s" />
    </s:Body>
  </s:Envelope>
"""


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--debug",
        action="store_true",
        help="debug mode: let Python exceptions come through",
    )
    parser.add_argument("--vcrtrace", action=vcrtrace())
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose mode")
    parser.add_argument(
        "-t",
        "--timeout",
        metavar="SEC",
        type=int,
        default=10,
        help="set the timeout for each query to <SEC> seconds (default: 10)",
    )
    parser.add_argument(
        "host_address",
        metavar="HOST",
        help="host name or IP address of your Fritz!Box",
    )

    return parser.parse_args(argv)


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.ERROR,
        format="%(levelname)s: %(message)s",
    )


class FritzConnection:
    def __init__(self, host_address: str, timeout: int) -> None:
        # Fritz!Box with firmware >= 6.0 use a new url.
        # Try the newer one first and switch if needed
        self._urlidx = 0
        self._urls: Final = (
            f"http://{host_address}:49000/upnp",
            f"http://{host_address}:49000/igdupnp",
        )
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-agent": "Check_MK agent_fritzbox",
                "Content-Type": "text/xml",
            }
        )

    def post(self, url: str, data: str, headers: Mapping[str, str]) -> requests.Response:
        return self._session.post(
            f"{self._urls[self._urlidx]}{url}", data=data, headers=headers, timeout=self._timeout
        )

    def toggle_base_url(self) -> None:
        self._urlidx = 1 - self._urlidx


def _get_response(
    control: str, namespace: str, action: str, connection: FritzConnection
) -> requests.Response:

    data = _SOAP_TEMPLATE % (action, namespace)

    for _retry in (0, 1):
        try:
            response = connection.post(
                f"/control/{control}", data, {"SoapAction": namespace + "#" + action}
            )
            response.raise_for_status()
            break  # got a good response
        except requests.exceptions.HTTPError:
            if response.status_code == 500:
                # old URL can not be found, select other base url in the hope that the other
                # url gets a successful result to have only one try on future requests
                connection.toggle_base_url()
        except Exception:
            logging.debug(traceback.format_exc())
            raise

    return response


def get_upnp_info(control: str, namespace: str, action: str, connection: FritzConnection):

    response = _get_response(control, namespace, action, connection)
    device, version = response.headers["SERVER"].split("UPnP/1.0 ")[1].rsplit(" ", 1)

    # parse the response body
    if (
        match := re.search(
            "<u:%sResponse[^>]+>(.*)</u:%sResponse>" % (action, action), response.text, re.M | re.S
        )
    ) is None:
        raise ValueError("Response not parsable")

    attrs = dict(re.findall("<([^>]+)>([^<]+)<[^>]+>", match.group(1), re.M | re.S))

    logging.debug("Parsed:\n%s", pprint.pformat(attrs))

    return attrs, device, version


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    args = parse_arguments(sys_argv)
    setup_logging(args.verbose)

    connection = FritzConnection(args.host_address, args.timeout)
    g_device, g_version = "", ""

    try:
        status = {}
        for control, namespace, action in _QUERIES:
            try:
                attrs, g_device, g_version = get_upnp_info(control, namespace, action, connection)
            except Exception:
                if args.debug:
                    raise
            else:
                status.update(attrs)

        sys.stdout.write("<<<fritz>>>\n")
        sys.stdout.write("VersionOS %s\n" % g_version)
        sys.stdout.write("VersionDevice %s\n" % g_device)
        for pair in status.items():
            sys.stdout.write("%s %s\n" % pair)

    except Exception:
        if args.debug:
            raise
        logging.error("Unhandled error: %s", traceback.format_exc())

    sys.stdout.write("<<<check_mk>>>\n")
    sys.stdout.write("AgentOS: FRITZ!OS\n")


if __name__ == "__main__":
    main()
