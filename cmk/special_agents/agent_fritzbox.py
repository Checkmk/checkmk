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
import socket
import sys
import traceback
import urllib.error
import urllib.request
from typing import Final

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


def get_upnp_info(control, namespace, action, base_urls):
    headers = {
        "User-agent": "Check_MK agent_fritzbox",
        "Content-Type": "text/xml",
        "SoapAction": namespace + "#" + action,
    }

    data = _SOAP_TEMPLATE % (action, namespace)

    # Fritz!Box with firmware >= 6.0 use a new url. We try the newer one first and
    # try the other one, when the first one did not succeed.
    for base_url in base_urls[:]:
        url = base_url + "/control/" + control
        logging.debug("URL: %s", url)
        logging.debug("SoapAction: %s", headers["SoapAction"])
        try:
            req = urllib.request.Request(url, data.encode("utf-8"), headers)
            handle = urllib.request.urlopen(req)
            break  # got a good response
        except urllib.error.HTTPError as e:
            if e.code == 500:
                # Is the result when the old URL can not be found, continue in this
                # case and revert the order of base urls in the hope that the other
                # url gets a successful result to have only one try on future requests
                # during an agent execution
                base_urls.reverse()
                continue
        except Exception:
            logging.debug(traceback.format_exc())
            raise

    infos = handle.info()
    contents = handle.read().decode("utf-8")

    parts = infos["SERVER"].split("UPnP/1.0 ")[1].split(" ")
    g_device = " ".join(parts[:-1])
    g_version = parts[-1]

    logging.debug("Server: %s", infos["SERVER"])
    logging.debug("%r", contents)

    # parse the response body
    match = re.search(
        "<u:%sResponse[^>]+>(.*)</u:%sResponse>" % (action, action), contents, re.M | re.S
    )
    if not match:
        raise ValueError("Response not parsable")
    response = match.group(1)
    matches = re.findall("<([^>]+)>([^<]+)<[^>]+>", response, re.M | re.S)

    attrs = {}
    for key, val in matches:
        attrs[key] = val

    logging.debug("Parsed:\n%s", pprint.pformat(attrs))

    return attrs, g_device, g_version


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    args = parse_arguments(sys_argv)
    setup_logging(args.verbose)

    socket.setdefaulttimeout(args.timeout)
    base_urls = [
        f"http://{args.host_address}:49000/upnp",
        f"http://{args.host_address}:49000/igdupnp",
    ]
    g_device, g_version = "", ""

    try:
        status = {}
        for control, namespace, action in _QUERIES:
            try:
                attrs, g_device, g_version = get_upnp_info(control, namespace, action, base_urls)
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
