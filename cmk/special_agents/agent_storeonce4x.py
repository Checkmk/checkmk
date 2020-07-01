#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK HP StoreOnce Special Agent for REST API Version 4.2.3"""

import argparse
import math
import sys
import collections
import json
import datetime as dt
from pathlib import Path
import logging
from typing import List, Any
import urllib3  # type: ignore[import]
from requests_oauthlib import OAuth2Session  # type: ignore[import]
from oauthlib.oauth2 import LegacyApplicationClient  # type: ignore[import]

from cmk.special_agents.utils import vcrtrace  # pylint: disable=cmk-module-layer-violation
import cmk.utils.paths

#   .--StoreOnce Oauth2----------------------------------------------------.
#   |            ____  _                  ___                              |
#   |           / ___|| |_ ___  _ __ ___ / _ \ _ __   ___ ___              |
#   |           \___ \| __/ _ \| '__/ _ \ | | | '_ \ / __/ _ \             |
#   |            ___) | || (_) | | |  __/ |_| | | | | (_|  __/             |
#   |           |____/ \__\___/|_|  \___|\___/|_| |_|\___\___|             |
#   |                                                                      |
#   |                   ___              _   _     ____                    |
#   |                  / _ \  __ _ _   _| |_| |__ |___ \                   |
#   |                 | | | |/ _` | | | | __| '_ \  __) |                  |
#   |                 | |_| | (_| | |_| | |_| | | |/ __/                   |
#   |                  \___/ \__,_|\__,_|\__|_| |_|_____|                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class StoreOnceOauth2Session:

    # TODO: In case of an update, the tmpfs will be deleted. This is no problem at first sight as a
    # new "fetch_token" will be triggered, however we should find better place for such tokens.
    _token_dir = Path(cmk.utils.paths.tmp_dir, "special_agents/agent_storeonce4x")
    _token_file_suffix = "%s_oAuthToken.json"
    _refresh_endpoint = "/pml/login/refresh"
    _token_endpoint = "/pml/login/authenticate"
    _dt_fmt = '%Y-%m-%d %H:%M:%S.%f'

    def __init__(self, host: str, port: str, user: str, secret: str, verify_ssl: bool) -> None:
        self._host = host
        self._token_file = self._token_file_suffix % self._host
        self._port = port
        self._user = user
        self._secret = secret
        self._verify_ssl = verify_ssl
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # We need to use LegacyClient due to grant_type==password
        self._client = LegacyApplicationClient(None)
        self._client.prepare_request_body(username=self._user, password=self._secret)

        # Check if token file exists, read it & create OAuthSession with it
        try:
            self._json_token = self.load_token_file_and_update_expire_in()
            LOGGER.debug("Loaded token content: %s", self._json_token)

            self._oauth_session = OAuth2Session(
                self._user,
                client=self._client,
                auto_refresh_url="https://%s:%s%s" %
                (self._host, self._port, self._refresh_endpoint),
                token_updater=self.store_token_file_and_update_expires_in_abs,
                token={
                    "access_token": self._json_token["access_token"],
                    "refresh_token": self._json_token["refresh_token"],
                    "expires_in": self._json_token["expires_in"]
                })

        except (FileNotFoundError, KeyError):
            LOGGER.debug("Token file not found or error in token file. Creating new connection.")
            self._oauth_session = OAuth2Session(
                self._user,
                client=self._client,
                auto_refresh_url="https://%s:%s%s" %
                (self._host, self._port, self._refresh_endpoint),
                token_updater=self.store_token_file_and_update_expires_in_abs)
            # Fetch token
            token_dict = self._oauth_session.fetch_token(
                token_url='https://%s:%s%s' % (self._host, self._port, self._token_endpoint),
                username=self._user,
                password=self._secret,
                verify=self._verify_ssl)
            # Initially create the token file
            self.store_token_file_and_update_expires_in_abs(token_dict)
            self._json_token = token_dict

    def store_token_file_and_update_expires_in_abs(self, token_dict: dict) -> None:
        if not self._token_dir.exists():
            self._token_dir.mkdir(parents=True)

        # Update expires_in_abs:
        # we need this to calculate a current "expires_in" (in seconds)
        token_dict["expires_in_abs"] = self.get_absolute_expire_time(token_dict["expires_in"])

        with open(self._token_file, "w") as token_file:
            json.dump(token_dict, token_file)

    def load_token_file_and_update_expire_in(self) -> dict:
        with open(self._token_file, "r") as token_file:
            token_json = json.load(token_file)

            # Update expires_in from expires_in_abs
            expires_in_abs = token_json["expires_in_abs"]
            expires_in_updated = dt.datetime.strptime(expires_in_abs,
                                                      self._dt_fmt) - dt.datetime.now()
            token_json["expires_in"] = math.floor(expires_in_updated.total_seconds())
            return token_json

    def get_absolute_expire_time(self, expires_in: str, expires_in_earlier: int = 20) -> str:
        """
        :param: expires_in_earlier: Will calculate an earlier absolute expire time about its
        value in [s].
        """
        # all expires_in are in seconds according to oAuth2 spec
        now = dt.datetime.now()
        dt_expires_in = dt.timedelta(0, float(expires_in))
        dt_expires_in_earlier = dt.timedelta(0, expires_in_earlier)
        return dt.datetime.strftime(now + dt_expires_in - dt_expires_in_earlier, self._dt_fmt)

    def execute_get_request(self, url: str) -> OAuth2Session.request:
        url = "https://%s:%s%s" % (self._host, self._port, url)
        resp = self._oauth_session.request(method="GET", url=url, verify=self._verify_ssl)
        if resp.status_code != 200:
            LOGGER.warning("Call to %s returned HTTP %s.", url, resp.status_code)
        return resp


#   .--handlers------------------------------------------------------------.
#   |               _                     _ _                              |
#   |              | |__   __ _ _ __   __| | | ___ _ __ ___                |
#   |              | '_ \ / _` | '_ \ / _` | |/ _ \ '__/ __|               |
#   |              | | | | (_| | | | | (_| | |  __/ |  \__ \               |
#   |              |_| |_|\__,_|_| |_|\__,_|_|\___|_|  |___/               |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def handler_simple(uris: List[str], opt: argparse.Namespace,
                   oauth_session: StoreOnceOauth2Session) -> None:
    for uri in uris:
        resp = oauth_session.execute_get_request(uri)
        sys.stdout.write("%s\n" % json.dumps(resp.json()))


def handler_appliances(uris: List[str], opt: argparse.Namespace,
                       oauth_session: StoreOnceOauth2Session) -> None:
    # Get all appliance UUIDs
    resp = oauth_session.execute_get_request(uris[0])
    sys.stdout.write("%s\n" % json.dumps(resp.json()))

    uuids = [mem["uuid"] for mem in resp.json()["members"]]
    # Get appliance's dashboard per UUID
    for uuid in uuids:
        resp = oauth_session.execute_get_request("%s/%s" % (uris[1], uuid))
        sys.stdout.write("%s\n" % json.dumps(resp.json()))


#   .--defines-------------------------------------------------------------.
#   |                      _       __ _                                    |
#   |                   __| | ___ / _(_)_ __   ___  ___                    |
#   |                  / _` |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | (_| |  __/  _| | | | |  __/\__ \                   |
#   |                  \__,_|\___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

LOGGER = logging.getLogger("agent_storeonce4x")

SECTION = collections.namedtuple('Section', ['name', 'uris', 'handler'])

# REST API 4.2.3 endpoint definitions
# https://hewlettpackard.github.io/storeonce-rest/cindex.html
BASE = "/api/v1"
SECTIONS = [
    SECTION("storeonce4x_d2d_services", [BASE + "/data-services/d2d-service/status"],
            handler_simple),
    SECTION("storeonce4x_rep_services", [BASE + "/data-services/rep/services"], handler_simple),
    SECTION("storeonce4x_vtl_services", [BASE + "/data-services/vtl/services"], handler_simple),
    SECTION("storeonce4x_alerts", ["/rest/alerts"], handler_simple),
    SECTION("storeonce4x_system_information", [BASE + "/management-services/system/information"],
            handler_simple),
    SECTION("storeonce4x_storage", [
        BASE + "/management-services/local-storage/overview",
    ], handler_simple),
    SECTION("storeonce4x_appliances", [
        BASE + "/management-services/federation/members",
        BASE + "/data-services/dashboard/appliance"
    ], handler_appliances),
    SECTION(
        "storeonce4x_licensing",
        [BASE + "/management-services/licensing", BASE + "/management-services/licensing/licenses"],
        handler_simple),
]

#   .--args----------------------------------------------------------------.
#   |                                                                      |
#   |                          __ _ _ __ __ _ ___                          |
#   |                         / _` | '__/ _` / __|                         |
#   |                        | (_| | | | (_| \__ \                         |
#   |                         \__,_|_|  \__, |___/                         |
#   |                                   |___/                              |
#   '----------------------------------------------------------------------'


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--vcrtrace",
                        "--tracefile",
                        action=vcrtrace(filter_headers=[('authorization', '****')]))

    parser.add_argument("user", metavar="USER", help="""Username for Observer Role""")
    parser.add_argument("password", metavar="PASSWORD", help="""Password for Observer Role""")

    parser.add_argument("-p",
                        "--port",
                        default=443,
                        type=int,
                        help="Use alternative port (default: 443)")

    parser.add_argument(
        "--verify_ssl",
        action="store_true",
        default=False,
    )
    parser.add_argument('--verbose', '-v', action="count", default=0)
    parser.add_argument("--debug",
                        action="store_true",
                        help="Debug mode: let Python exceptions come through")

    parser.add_argument("host", metavar="HOST", help="""APPLIANCE-ADDRESS of HP StoreOnce""")

    return parser.parse_args(argv)


#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def main(argv: Any = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    opt = parse_arguments(argv)

    if not opt.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        level={
            0: logging.WARN,
            1: logging.INFO,
            2: logging.DEBUG
        }.get(opt.verbose, logging.DEBUG),
    )

    LOGGER.debug("Calling agent_storeonce4x with parameters: %s", opt.__repr__())

    oauth_session = StoreOnceOauth2Session(opt.host, opt.port, opt.user, opt.password,
                                           opt.verify_ssl)

    try:
        for section in SECTIONS:
            sys.stdout.write("<<<%s:sep(0)>>>\n" % section.name)
            section.handler(section.uris, opt, oauth_session)
    except Exception as exc:
        if opt.debug:
            raise
        LOGGER.error("Caught exception: %r", exc)
        return -1

    return 0


if __name__ == "__main__":
    main()
