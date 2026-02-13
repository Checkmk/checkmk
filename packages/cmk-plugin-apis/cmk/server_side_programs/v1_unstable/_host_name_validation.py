#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Never

from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPSConnection


class HostnameValidationAdapter(HTTPAdapter):
    """An HTTPAdapter that enforces hostname validation against a given hostname.

    In Checkmk we often find ourselves in situations where we want to connect to a server via
    its IP address, but the server's SSL certificate is issued for a hostname. This adapter allows
    us to enforce hostname validation against the expected hostname, even when connecting via IP.

    Example::

        #!/usr/bin/env/python3
        ...
        address = "[12600:1406:5e00:6::17ce:bc1b]"  # this how we contact the server
        cert_server_name = "example.com"  # this is the name we expect in the server's certificate
        session = requests.Session()

        session.mount(f"https://{address}", HostnameValidationAdapter(cert_server_name))

        response = session.get(f"https://{address}/some/api/endpoint")
        ...


    """

    def __init__(self, hostname: str) -> None:
        super().__init__()
        self._reference_hostname = hostname

    def cert_verify(self, conn: HTTPSConnection, url: Never, verify: Never, cert: Never) -> None:
        """Verify a SSL certificate. This method should not be called from user code.

        Since the superclass method is untyped anyway, we type the arguments as Never
        to indicate that this function should not be called in normal usage.
        """
        conn.assert_hostname = self._reference_hostname
        super().cert_verify(conn, url, verify, cert)  # type: ignore[no-untyped-call]
