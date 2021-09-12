#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK HP StoreOnce Special Agent for REST API Version 4.2.3"""

# TODO: once this agent can be used on a 2.x live system, it should be checked for functionality
#       and against known exceptions

import datetime as dt
import json
import logging
import math
from pathlib import Path
from typing import Any, Callable, Generator, Optional, Sequence, Tuple

import urllib3  # type: ignore[import]
from oauthlib.oauth2 import LegacyApplicationClient  # type: ignore[import]
from requests_oauthlib import OAuth2Session  # type: ignore[import]

import cmk.utils.paths

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.utils.request_helper import Requester, StringMap, to_token_dict, TokenDict

AnyGenerator = Generator[Any, None, None]
ResultFn = Callable[..., AnyGenerator]

LOGGER = logging.getLogger("agent_storeonce4x")


class StoreOnceOauth2Session(Requester):

    # TODO: In case of an update, the tmpfs will be deleted. This is no problem at first sight as a
    # new "fetch_token" will be triggered, however we should find better place for such tokens.
    _token_dir = Path(cmk.utils.paths.tmp_dir, "special_agents/agent_storeonce4x")
    _token_file_suffix = "%s_oAuthToken.json"
    _refresh_endpoint = "/pml/login/refresh"
    _token_endpoint = "/pml/login/authenticate"
    _dt_fmt = "%Y-%m-%d %H:%M:%S.%f"

    def __init__(self, host: str, port: str, user: str, secret: str, verify_ssl: bool) -> None:
        self._host = host
        self._token_file = "%s/%s" % (str(self._token_dir), self._token_file_suffix % self._host)
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
                auto_refresh_url="https://%s:%s%s"
                % (self._host, self._port, self._refresh_endpoint),
                token_updater=lambda x: self.store_token_file_and_update_expires_in_abs(
                    to_token_dict(x)
                ),
                token={
                    "access_token": self._json_token["access_token"],
                    "refresh_token": self._json_token["refresh_token"],
                    "expires_in": self._json_token["expires_in"],
                },
            )
        except (FileNotFoundError, KeyError):
            LOGGER.debug("Token file not found or error in token file. Creating new connection.")
            self._oauth_session = OAuth2Session(
                self._user,
                client=self._client,
                auto_refresh_url="https://%s:%s%s"
                % (self._host, self._port, self._refresh_endpoint),
                token_updater=lambda x: self.store_token_file_and_update_expires_in_abs(
                    to_token_dict(x)
                ),
            )
            # Fetch token
            token_dict = to_token_dict(
                self._oauth_session.fetch_token(
                    token_url="https://%s:%s%s" % (self._host, self._port, self._token_endpoint),
                    username=self._user,
                    password=self._secret,
                    verify=self._verify_ssl,
                )
            )
            # Initially create the token file
            self.store_token_file_and_update_expires_in_abs(token_dict)
            self._json_token = token_dict

    def store_token_file_and_update_expires_in_abs(self, token_dict: TokenDict) -> None:
        if not self._token_dir.exists():
            self._token_dir.mkdir(parents=True)

        # Update expires_in_abs:
        # we need this to calculate a current "expires_in" (in seconds)
        token_dict["expires_in_abs"] = self.get_absolute_expire_time(token_dict["expires_in"])

        with open(self._token_file, "w") as token_file:
            json.dump(token_dict, token_file)

    def load_token_file_and_update_expire_in(self) -> TokenDict:
        with open(self._token_file, "r") as token_file:
            token_json = json.load(token_file)

            # Update expires_in from expires_in_abs
            expires_in_abs = token_json["expires_in_abs"]
            expires_in_updated = (
                dt.datetime.strptime(
                    expires_in_abs,
                    self._dt_fmt,
                )
                - dt.datetime.now()
            )
            token_json["expires_in"] = math.floor(expires_in_updated.total_seconds())
            return to_token_dict(token_json)

    def get_absolute_expire_time(self, expires_in: float, expires_in_earlier: int = 20) -> str:
        """
        :param: expires_in_earlier: Will calculate an earlier absolute expire time about its
        value in [s].
        """
        # all expires_in are in seconds according to oAuth2 spec
        now = dt.datetime.now()
        dt_expires_in = dt.timedelta(0, expires_in)
        dt_expires_in_earlier = dt.timedelta(0, expires_in_earlier)
        return dt.datetime.strftime(now + dt_expires_in - dt_expires_in_earlier, self._dt_fmt)

    def get(self, path: str, parameters: Optional[StringMap] = None) -> Any:
        url = "https://%s:%s%s" % (self._host, self._port, path)
        resp = self._oauth_session.request(
            method="GET",
            headers={"Accept": "application/json"},
            url=url,
            verify=self._verify_ssl,
        )
        if resp.status_code != 200:
            LOGGER.warning("Call to %s returned HTTP %s.", url, resp.status_code)
        return resp.json()


def handler_simple(requester: Requester, uris: Sequence[str]) -> AnyGenerator:
    yield from (requester.get(uri) for uri in uris)


def handler_nested(requester: Requester, uris: Sequence[str], identifier: str) -> AnyGenerator:
    # Get all appliance UUIDs
    members = requester.get(uris[0])
    yield members

    # Get appliance's dashboard per UUID
    for member in members["members"]:
        yield requester.get("%s/%s" % (uris[1], member[identifier]))


# REST API 4.2.3 endpoint definitions
# https://hewlettpackard.github.io/storeonce-rest/cindex.html
BASE = "/api/v1"
SECTIONS: Sequence[Tuple[str, ResultFn]] = (
    (
        "d2d_services",
        lambda conn: handler_simple(
            conn,
            (BASE + "/data-services/d2d-service/status",),
        ),
    ),
    (
        "rep_services",
        lambda conn: handler_simple(
            conn,
            (BASE + "/data-services/rep/services",),
        ),
    ),
    (
        "vtl_services",
        lambda conn: handler_simple(
            conn,
            (BASE + "/data-services/vtl/services",),
        ),
    ),
    (
        "alerts",
        lambda conn: handler_simple(
            conn,
            ("/rest/alerts",),
        ),
    ),
    (
        "system_information",
        lambda conn: handler_simple(
            conn,
            (BASE + "/management-services/system/information",),
        ),
    ),
    (
        "storage",
        lambda conn: handler_simple(
            conn,
            (BASE + "/management-services/local-storage/overview",),
        ),
    ),
    (
        "appliances",
        lambda conn: handler_nested(
            conn,
            (
                BASE + "/management-services/federation/members",
                BASE + "/data-services/dashboard/appliance",
            ),
            "uuid",
        ),
    ),
    (
        "licensing",
        lambda conn: handler_simple(
            conn,
            (
                BASE + "/management-services/licensing",
                BASE + "/management-services/licensing/licenses",
            ),
        ),
    ),
    (
        "cat_stores",
        lambda conn: handler_nested(
            conn,
            (
                BASE + "/data-services/cat/stores",
                BASE + "/data-services/cat/stores/store",
            ),
            "id",
        ),
    ),
)


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("user", metavar="USER", help="""Username for Observer Role""")
    parser.add_argument("password", metavar="PASSWORD", help="""Password for Observer Role""")
    parser.add_argument(
        "-p", "--port", default=443, type=int, help="Use alternative port (default: 443)"
    )

    parser.add_argument("--verify_ssl", action="store_true", default=False)
    parser.add_argument("host", metavar="HOST", help="""APPLIANCE-ADDRESS of HP StoreOnce""")
    return parser.parse_args(argv)


def agent_storeonce4x_main(args: Args) -> None:
    if not args.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    oauth_session = StoreOnceOauth2Session(
        args.host,
        args.port,
        args.user,
        args.password,
        args.verify_ssl,
    )

    for section_basename, function in SECTIONS:
        with SectionWriter("storeonce4x_%s" % section_basename) as writer:
            try:
                writer.append_json(function(oauth_session))
            except Exception as exc:
                if args.debug:
                    raise
                LOGGER.error("Caught exception: %r", exc)


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_storeonce4x_main)


if __name__ == "__main__":
    main()
