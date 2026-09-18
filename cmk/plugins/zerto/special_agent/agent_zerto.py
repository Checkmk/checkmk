#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_zerto

Checkmk special agent for monitoring Zerto application.
"""

# mypy: disable-error-code="no-any-return"

import argparse
import logging
import sys
from collections.abc import Mapping, Sequence
from urllib.parse import urljoin

from requests import Response, Session
from requests.auth import HTTPBasicAuth

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter

LOGGER = logging.getLogger(__name__)

PASSWORD_OPTION = "password"


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)

    # flags
    parser.add_argument(
        "-a", "--authentication", default="windows", type=str, help="Authentication method"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Debug mode: raise Python exceptions"
    )
    parser.add_argument("-v", "--verbose", action="count", help="Be more verbose")
    parser.add_argument("-u", "--username", required=True, help="Zerto user name")
    parser_add_secret_option(
        parser, long=f"--{PASSWORD_OPTION}", required=True, help="Zerto use password"
    )
    parser.add_argument("hostaddress", help="Zerto host name")
    parser.add_argument(
        "--disable-cert-verification",
        action="store_true",
        help="Do not verify TLS certificate.",
    )
    parser.add_argument(
        "--cert-server-name",
        required=True,
        help="Use this server name for TLS certificate validation",
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
    logging.basicConfig(level=lvl, format=fmt)  # astrein: disable=logging-formatter

    return args


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
            timeout=900,
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


class ZertoRequest:
    def __init__(
        self,
        base_url: str,
        session_id: str | None,
        verify: bool,
        validation: HostnameValidationAdapter,
    ) -> None:
        self._base_url = base_url
        self._headers = {"x-zerto-session": str(session_id), "content-type": "application/json"}
        self._verify = verify
        self._validation = validation

    def get_vms_data(self) -> Sequence[dict[str, str]]:
        response = ApiSession(
            self._base_url,
            tls_cert_verification=self._validation if self._verify else False,
            additional_headers=self._headers,
        ).get("/vms")

        if response.status_code != 200:
            LOGGER.debug(
                "response status code: %(status_code)s", {"status_code": response.status_code}
            )
            LOGGER.debug("response : %(text)s", {"text": response.text})
            raise RuntimeError("Call to ZVM failed")
        try:
            data = response.json()
        except ValueError:
            LOGGER.debug("failed to parse json")
            LOGGER.debug("response : %(text)s", {"text": response.text})
            raise ValueError("Got invalid data from host")
        return data


class ZertoConnection:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify: bool,
        validation: HostnameValidationAdapter,
    ) -> None:
        self._username = username
        self._password = password
        self._base_url = base_url
        self._verify = verify
        self._validation = validation

    def get_session_id(self, authentication: str) -> str | None:
        if authentication == "windows":
            response = ApiSession(
                self._base_url,
                auth=HTTPBasicAuth(self._username, self._password),
                tls_cert_verification=self._validation if self._verify else False,
            ).request("post", "/session/add")

        else:
            response = ApiSession(
                self._base_url,
                auth=HTTPBasicAuth(self._username, self._password),
                tls_cert_verification=self._validation if self._verify else False,
                additional_headers={"content-type": "application/json"},
            ).request("post", "/session/add")

        if response.status_code != 200:
            LOGGER.info(
                "response status code: %(status_code)s", {"status_code": response.status_code}
            )
            LOGGER.debug("response text: %(text)s", {"text": response.text})
            raise AuthError("Failed authenticating to the Zerto Virtual Manager")

        if "x-zerto-session" not in response.headers:
            LOGGER.info("session id not found in response header")
            LOGGER.debug("response header: %(headers)s", {"headers": response.headers})
            LOGGER.debug("response text: %(text)s", {"text": response.text})
        return response.headers.get("x-zerto-session")


class AuthError(Exception):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv or sys.argv[1:])
    base_url = f"https://{args.hostaddress}:9669/v1"

    sys.stdout.write("<<<zerto_agent:sep(0)>>>\n")
    try:
        connection = ZertoConnection(
            base_url,
            args.username,
            resolve_secret_option(args, PASSWORD_OPTION).reveal(),
            verify=not args.disable_cert_verification,
            validation=HostnameValidationAdapter(args.cert_server_name),
        )
        session_id = connection.get_session_id(args.authentication)
    except Exception as e:
        sys.stdout.write(f"Error: {e}\n")
        return 1
    sys.stdout.write("Initialized OK\n")

    request = ZertoRequest(
        base_url,
        session_id,
        verify=not args.disable_cert_verification,
        validation=HostnameValidationAdapter(args.cert_server_name),
    )
    vm_data = request.get_vms_data()
    for vm in vm_data:
        try:
            sys.stdout.write("<<<<{}>>>>\n".format(vm["VmName"]))
            sys.stdout.write("<<<zerto_vpg_rpo:sep(124)>>>\n")
            sys.stdout.write("{}|{}|{}\n".format(vm["VpgName"], vm["Status"], vm["ActualRPO"]))
            sys.stdout.write("<<<<>>>>\n")
        except KeyError:
            continue
    return 0


if __name__ == "__main__":
    sys.exit(main())
