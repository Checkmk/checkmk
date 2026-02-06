#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_hp_msa

Checkmk special agent for monitoring HP MSA storage systems.
"""

# mypy: disable-error-code="type-arg"

import argparse
import hashlib
import logging
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests
import urllib3
from requests.structures import CaseInsensitiveDict

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option

LOGGER = logging.getLogger(__name__)

PASSWORD_OPTION = "password"


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)

    # flags
    parser.add_argument("-v", "--verbose", action="count", help="""Increase verbosity""")
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: let Python exceptions come through"""
    )

    parser.add_argument("hostaddress", help="HP MSA host name")
    parser.add_argument("-u", "--username", required=True, help="HP MSA user name")
    parser_add_secret_option(
        parser, long=f"--{PASSWORD_OPTION}", required=True, help="HP MSA user password"
    )

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
sections: dict[str, list[str]] = {}

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


def store_property(prop: list[str]) -> None:
    if prop[0] in property_to_section:
        LOGGER.info("property (stored): %r", (prop,))
        sections.setdefault(property_to_section[prop[0]], []).append(" ".join(prop))
    else:
        LOGGER.debug("property (ignored): %r", (prop,))


class HTMLObjectParser(HTMLParser):
    def feed(self, data: str) -> None:
        self.current_object_key: list[str | None] | None = None
        self.current_property: list[str | None] | None = None
        HTMLParser.feed(self, data)

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str | None]]) -> None:
        if tag == "object":
            keys = dict(attrs)
            self.current_object_key = [keys["basetype"], keys["oid"]]
        elif tag == "property":
            keys = dict(attrs)
            if self.current_object_key:
                self.current_property = self.current_object_key + [keys["name"]]

    def handle_endtag(self, tag: str) -> None:
        if tag in ["property", "object"]:
            if self.current_property:
                store_property([k for k in self.current_property if k is not None])
            self.current_property = None
            if tag == "object":
                self.current_object_key = None

    def handle_data(self, data: str) -> None:
        if self.current_property:
            self.current_property.append(data.replace("\n", "").replace("\r", ""))


class AuthError(RuntimeError):
    pass


class HPMSAConnection:
    def __init__(self, *, hostaddress: str, username: str, password: str, timeout: int) -> None:
        self._host = hostaddress
        self._base_url = f"https://{self._host}/api/"
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers = CaseInsensitiveDict({"User-agent": "Checkmk special agent_hp_msa"})
        # we cannot use self._session.verify because it will be overwritten by
        # the REQUESTS_CA_BUNDLE env variable
        self._verify_ssl = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._login(username, password)

    def __enter__(self) -> "HPMSAConnection":
        return self

    def __exit__(self, *args: object) -> None:
        self._logout()

    def _login(self, username: str, password: str) -> None:
        try:
            session_key = self._get_session_key(hashlib.sha256, username, password)
        except (requests.exceptions.ConnectionError, AuthError):
            LOGGER.warning("Could not connect via /api/, retry with /v3/api.")
            self._base_url = f"https://{self._host}/v3/api/"
            session_key = self._get_session_key(hashlib.md5, username, password)

        self._session.headers.update(sessionKey=session_key)

    def _logout(self) -> None:
        if not (session_key := self._session.headers.pop("sessionKey", None)):
            LOGGER.warning("No session key found during logout")
            return
        self.get(uri=f"logout/{str(session_key)}")
        LOGGER.debug("Successfully logged out from HP MSA device")

    def _get_session_key(self, hash_class: Callable, username: str, password: str) -> str:
        login_hash = hash_class()
        login_hash.update(f"{username}_{password}".encode())
        login_uri = f"login/{login_hash.hexdigest()}"
        response = self.get(uri=login_uri)
        xml_tree = ET.fromstring(response.text)
        response_element = xml_tree.find("./OBJECT/PROPERTY[@name='response']")
        if response_element is None:
            raise Exception("no response element")
        session_key = response_element.text
        if not isinstance(session_key, str):
            raise Exception("invalid response element")
        if session_key.lower() == "authentication unsuccessful":
            raise AuthError(
                f"Connecting to {self._base_url} failed. Please verify host address & login details"
            )
        return session_key

    def get(self, *, uri: str) -> requests.Response:
        url = urljoin(self._base_url, uri)
        LOGGER.debug("GET %r", url)
        # we must provide the verify keyword to every individual request call!
        response = self._session.get(url, timeout=self._timeout, verify=self._verify_ssl)
        if response.status_code != 200:
            LOGGER.warning(
                "RESPONSE.status_code, reason: %r", (response.status_code, response.reason)
            )
        LOGGER.debug("RESPONSE.text\n%s", response.text)
        return response


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv or sys.argv[1:])
    opt_timeout = 10
    parser = HTMLObjectParser()

    with HPMSAConnection(
        hostaddress=args.hostaddress,
        username=args.username,
        password=resolve_secret_option(args, PASSWORD_OPTION).reveal(),
        timeout=opt_timeout,
    ) as connection:
        for element in api_get_objects:
            response = connection.get(uri="show/%s" % element)
            try:
                parser.feed(response.text)
            except Exception as exc:  # broad exception because we don't know what to catch
                if args.debug:
                    raise
                LOGGER.warning("Failed to parse response for %s: %s", element, exc)

    # Output sections
    for section, lines in sections.items():
        sys.stdout.write("<<<hp_msa_%s>>>\n" % section)
        sys.stdout.write("\n".join(lines))
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
