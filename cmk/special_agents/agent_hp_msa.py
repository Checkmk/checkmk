#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import hashlib
import logging
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Dict
from urllib.parse import urljoin

import requests
import urllib3
from requests.structures import CaseInsensitiveDict

from cmk.utils.password_store import replace_passwords

LOGGER = logging.getLogger(__name__)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)

    # flags
    parser.add_argument("-v", "--verbose", action="count", help="""Increase verbosity""")
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: let Python exceptions come through"""
    )

    parser.add_argument("hostaddress", help="HP MSA host name")
    parser.add_argument("-u", "--username", required=True, help="HP MSA user name")
    parser.add_argument("-p", "--password", required=True, help="HP MSA user password")

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


# The dict key is the section, the values the list of lines
sections: Dict = {}

# Which objects to get
api_get_objects = [
    "controllers",
    "controller-statistics",
    "disks",
    "disk-statistics",
    "frus",
    "port",
    "host-port-statistics",
    "power-supplies",
    "system",
    "volumes",
    "volume-statistics",
]

# Where to put the properties from any response
# There is no mapping of object:property -> check_mk section, so far
# Just a simple mapping of property -> check_mk section
property_to_section = {
    "controller-statistics": "controller",
    "controller": "controller",
    "disk-statistics": "disk",
    "drives": "disk",
    "enclosure-fru": "fru",
    "port": "if",
    "fc-port": "if",
    "host-port-statistics": "if",
    "power-supplies": "psu",
    "fan": "fan",
    "system": "system",
    "redundancy": "system",
    "volumes": "volume",
    "volume-statistics": "volume",
}


def store_property(prop):
    if prop[0] in property_to_section:
        LOGGER.info("property (stored): %r", (prop,))
        sections.setdefault(property_to_section[prop[0]], []).append(" ".join(prop))
    else:
        LOGGER.debug("property (ignored): %r", (prop,))


class HTMLObjectParser(HTMLParser):
    def feed(self, data):
        self.current_object_key = None
        self.current_property = None
        HTMLParser.feed(self, data)

    def handle_starttag(self, tag, attrs):
        if tag == "object":
            keys = dict(attrs)
            self.current_object_key = [keys["basetype"], keys["oid"]]
        elif tag == "property":
            keys = dict(attrs)
            if self.current_object_key:
                self.current_property = self.current_object_key + [keys["name"]]

    def handle_endtag(self, tag):
        if tag in ["property", "object"]:
            if self.current_property:
                store_property(self.current_property)
            self.current_property = None
            if tag == "object":
                self.current_object_key = None

    def handle_data(self, data):
        if self.current_property:
            self.current_property.append(data.replace("\n", "").replace("\r", ""))


class AuthError(RuntimeError):
    pass


class HPMSAConnection:
    def __init__(self, hostaddress, opt_timeout, debug):
        self._host = hostaddress
        self._base_url = "https://%s/api/" % self._host
        self._timeout = opt_timeout
        self._session = requests.Session()
        self._session.headers = CaseInsensitiveDict({"User-agent": "Checkmk special agent_hp_msa"})
        # we cannot use self._session.verify because it will be overwritten by
        # the REQUESTS_CA_BUNDLE env variable
        self._verify_ssl = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._debug = debug

    def login(self, username, password):
        try:
            session_key = self._get_session_key(hashlib.sha256, username, password)
        except (requests.exceptions.ConnectionError, AuthError):
            # Try to connect to old API if no connection to new API can be established
            self._base_url = "https://%s/v3/api/" % self._host
            session_key = self._get_session_key(hashlib.md5, username, password)

        self._session.headers.update(sessionKey=session_key)

    def _get_session_key(self, hash_class, username, password):
        login_hash = hash_class()
        login_hash.update(f"{username}_{password}".encode("utf-8"))
        login_url = "login/%s" % login_hash.hexdigest()
        response = self.get(login_url)
        xml_tree = ET.fromstring(response.text)
        response_element = xml_tree.find("./OBJECT/PROPERTY[@name='response']")
        if response_element is None:
            raise Exception("no response element")
        session_key = response_element.text
        if not isinstance(session_key, str):
            raise Exception("invalid response element")
        if session_key.lower() == "authentication unsuccessful":
            raise AuthError(
                "Connecting to %s failed. Please verify host address & login details"
                % self._base_url
            )
        return session_key

    def get(self, url_suffix):
        url = urljoin(self._base_url, url_suffix)
        LOGGER.info("GET %r", url)
        # we must provide the verify keyword to every individual request call!
        response = self._session.get(url, timeout=self._timeout, verify=self._verify_ssl)
        if response.status_code != 200:
            LOGGER.warning(
                "RESPONSE.status_code, reason: %r", (response.status_code, response.reason)
            )
        LOGGER.debug("RESPONSE.text\n%s", response.text)
        return response


def main(argv=None):
    replace_passwords()
    args = parse_arguments(argv or sys.argv[1:])
    opt_timeout = 10

    connection = HPMSAConnection(args.hostaddress, opt_timeout, args.debug)
    connection.login(args.username, args.password)
    parser = HTMLObjectParser()

    for element in api_get_objects:
        response = connection.get("show/%s" % element)
        try:
            parser.feed(response.text)
        except Exception:
            if args.debug:
                raise

    # Output sections
    for section, lines in sections.items():
        print("<<<hp_msa_%s>>>" % section)
        print("\n".join(x for x in lines))

    return 0
