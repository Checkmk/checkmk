#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_alertmanager

Checkmk special agent for monitoring Prometheus Alertmanager.
"""

# mypy: disable-error-code="no-any-return"

import argparse
import ast
import json
import logging
import sys
import traceback
from argparse import Namespace
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict
from urllib.parse import urljoin

import requests
from requests import Response, Session
from requests.auth import HTTPBasicAuth

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter

PASSWORD_OPTION = "password"
TOKEN_OPTION = "token"


class ApiSession:
    """Class for issuing multiple API calls

    ApiSession behaves similar to requests.Session with the exception that a
    base URL is provided and persisted.
    All requests use the base URL and append the provided url to it.
    """

    def __init__(
        self,
        base_url: str,
        auth: HTTPBasicAuth | None = None,
        tls_cert_verification: bool | HostnameValidationAdapter = True,
        additional_headers: Mapping[str, str] | None = None,
    ):
        self._session = Session()
        self._session.auth = auth
        self._session.headers.update(additional_headers or {})
        self._base_url = base_url

        if isinstance(tls_cert_verification, HostnameValidationAdapter):
            self._session.mount(self._base_url, tls_cert_verification)
            self.verify = True
        else:
            self.verify = tls_cert_verification

    def request(
        self,
        method: str,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self._session.request(
            method,
            urljoin(self._base_url, url),
            params=params,
            verify=self.verify,
        )

    def get(
        self,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self.request(
            "get",
            url,
            params=params,
        )


@dataclass(frozen=True, kw_only=True)
class LoginAuth:
    username: str
    password: str


@dataclass(frozen=True)
class TokenAuth:
    token: str


def authentication_from_args(args: Namespace) -> LoginAuth | TokenAuth | None:
    match args.auth_method:
        case "auth_login":
            return LoginAuth(
                username=args.username,
                password=resolve_secret_option(args, PASSWORD_OPTION).reveal(),
            )
        case "auth_token":
            return TokenAuth(resolve_secret_option(args, TOKEN_OPTION).reveal())
        case _:
            return None


def get_api_url(connection: str, protocol: Literal["http", "https"]) -> str:
    return f"{protocol}://{connection}/api/v1/"


def generate_api_session(
    api_url: str,
    authentication: LoginAuth | TokenAuth | None,
    tls_cert_verification: bool | str,
) -> ApiSession:
    tls_cert_verification_: bool | HostnameValidationAdapter = (
        tls_cert_verification
        if isinstance(tls_cert_verification, bool)
        else HostnameValidationAdapter(tls_cert_verification)
    )
    match authentication:
        case LoginAuth(username=username, password=password):
            return ApiSession(
                api_url,
                auth=HTTPBasicAuth(username, password),
                tls_cert_verification=tls_cert_verification_,
            )
        case TokenAuth(token):
            return ApiSession(
                api_url,
                tls_cert_verification=tls_cert_verification_,
                additional_headers={"Authorization": "Bearer " + token},
            )
        case _:
            return ApiSession(
                api_url,
                tls_cert_verification=tls_cert_verification_,
            )


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: raise Python exceptions"""
    )
    parser.add_argument(
        "--config",
        required=True,
        help="The configuration is passed as repr object. This option will change in the future.",
    )
    auth_method_subparsers = parser.add_subparsers(
        dest="auth_method",
        metavar="AUTH-METHOD",
        help="API authentication method",
    )

    parser_auth_login = auth_method_subparsers.add_parser(
        "auth_login",
        help="Authentication with username and password",
    )
    parser_auth_login.add_argument(
        "--username",
        required=True,
        metavar="USERNAME",
    )
    parser_add_secret_option(
        parser_auth_login,
        long=f"--{PASSWORD_OPTION}",
        required=True,
        help="The password for API authentication.",
    )

    parser_auth_token = auth_method_subparsers.add_parser(
        "auth_token",
        help="Authentication with token",
    )
    parser_add_secret_option(
        parser_auth_token,
        long=f"--{TOKEN_OPTION}",
        required=True,
        help="Password store reference of the token for API authentication.",
    )
    parser.add_argument(
        "--disable-cert-verification",
        action="store_true",
        help="Do not verify TLS certificate.",
    )
    args = parser.parse_args(argv)
    return args


class IgnoreAlerts(TypedDict):
    ignore_na: NotRequired[bool]
    ignore_alert_rules: list[str]
    ignore_alert_groups: list[str]


class Rule(TypedDict):
    name: str
    state: str
    severity: str | None
    message: str | None


Groups = dict[str, list[Rule]]


class AlertmanagerAPI:
    """
    Realizes communication with the Alertmanager API
    """

    def __init__(self, session: ApiSession) -> None:
        self.session = session

    def query_static_endpoint(self, endpoint: str) -> requests.models.Response:
        """Query the given endpoint of the Alertmanager API expecting a text response

        Args:
            endpoint: Param which contains the Prometheus API endpoint to be queried

        Returns:
            Returns a response containing the text response
        """
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response


def alertmanager_rules_section(
    api_client: AlertmanagerAPI,
    config: dict[str, Any],
) -> None:
    rule_groups = retrieve_rule_data(api_client)
    if not rule_groups.get("groups"):
        return
    parsed_data = parse_rule_data(rule_groups["groups"], config["ignore_alerts"])

    sys.stdout.write(
        f"<<<<{config['hostname']}>>>>\n"  # could be empty, that's ok.
        "<<<alertmanager:sep(0)>>>\n"
        f"{json.dumps(parsed_data, sort_keys=True)}\n"
    )


def retrieve_rule_data(api_client: AlertmanagerAPI) -> dict[str, Any]:
    endpoint_result = api_client.query_static_endpoint("rules")
    return json.loads(endpoint_result.content)["data"]


def parse_rule_data(group_data: list[dict[str, Any]], ignore_alerts: IgnoreAlerts) -> Groups:
    """Parses data from Alertmanager API endpoint

    Args:
        data: Raw  unparsed data from Alertmanager API endpoint

    Returns:
        Returns a dict of all alert rule groups containing a list
        of all alert rules within the group
    """
    groups: Groups = {}
    for group_entry in group_data:
        if group_entry["name"] in ignore_alerts["ignore_alert_groups"]:
            continue
        rule_list = []
        for rule_entry in group_entry["rules"]:
            if rule_entry["name"] in ignore_alerts["ignore_alert_rules"] or (
                ignore_alerts.get("ignore_na", False) and not rule_entry.get("state", False)
            ):
                continue

            labels = rule_entry.get("labels", {})
            annotations = rule_entry.get("annotations", {})
            rule_list.append(
                Rule(
                    name=rule_entry["name"],
                    state=rule_entry.get("state"),
                    severity=labels.get("severity"),
                    message=annotations.get("message"),
                )
            )
        groups[group_entry["name"]] = rule_list
    return groups


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)
    try:
        config = ast.literal_eval(args.config)
        session = generate_api_session(
            get_api_url(config["connection"], config["protocol"]),
            authentication_from_args(args),
            not args.disable_cert_verification,
        )
        api_client = AlertmanagerAPI(session)
        alertmanager_rules_section(api_client, config)
    except Exception as e:
        if args.debug:
            raise
        logging.debug(traceback.format_exc())
        sys.stderr.write("%s\n" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
