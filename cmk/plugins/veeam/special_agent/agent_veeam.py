#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_veeam

Checkmk special agent for Veeam Backup & Replication.

Queries the REST API of a Veeam backup server over the network, so that nothing
has to be installed on the backup server itself. This module currently only
establishes the connection; the sections are added by the follow-up work.
"""

import argparse
import sys
from collections.abc import Sequence

import requests

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter

PASSWORD_OPTION = "password"


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--user", required=True, help="Veeam user name")
    parser_add_secret_option(
        parser, long=f"--{PASSWORD_OPTION}", required=True, help="Password of the Veeam user"
    )
    parser.add_argument(
        "--port", type=int, default=9419, help="Port of the Veeam REST API (default: 9419)"
    )

    tls = parser.add_mutually_exclusive_group(required=True)
    tls.add_argument(
        "--cert-server-name",
        help="Validate the server certificate against this host name",
    )
    tls.add_argument(
        "--disable-cert-verification",
        action="store_true",
        help="Do not verify the server certificate",
    )

    parser.add_argument("address", help="Address of the Veeam backup server")

    return parser.parse_args(argv)


def base_url(address: str, port: int) -> str:
    return f"https://{address}:{port}"


def create_session(url: str, cert_server_name: str | None) -> requests.Session:
    """Build the session used for all API calls.

    We may be talking to an IP address while the certificate is issued for a host
    name, so certificate validation is pinned to `cert_server_name` rather than to
    whatever we dialled.
    """
    session = requests.Session()
    if cert_server_name is None:
        session.verify = False
    else:
        session.mount(url, HostnameValidationAdapter(cert_server_name))
    return session


def write_sections(session: requests.Session, user: str, password: str) -> None:
    """Query the REST API and write the agent sections.

    Authentication (OAuth2 against ``/api/oauth2/token``) and the sections
    themselves are added by the follow-up work. For now the special agent only
    establishes the connection.
    """


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(sys.argv[1:] if argv is None else argv)

    with create_session(
        base_url(args.address, args.port),
        None if args.disable_cert_verification else args.cert_server_name,
    ) as session:
        write_sections(session, args.user, resolve_secret_option(args, PASSWORD_OPTION).reveal())

    return 0


if __name__ == "__main__":
    sys.exit(main())
