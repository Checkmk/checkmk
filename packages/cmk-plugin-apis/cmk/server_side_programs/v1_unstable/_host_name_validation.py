#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Never, override

from requests.adapters import DEFAULT_POOLBLOCK, HTTPAdapter
from requests.models import PreparedRequest, Response
from urllib3.connection import HTTPSConnection
from urllib3.poolmanager import PoolManager


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
        self._reference_hostname = hostname
        super().__init__()

    @override
    def cert_verify(self, conn: HTTPSConnection, url: Never, verify: Never, cert: Never) -> None:
        """Verify a SSL certificate. This method should not be called from user code.

        Since the superclass method is untyped anyway, we type the arguments as Never
        to indicate that this function should not be called in normal usage.
        """
        conn.assert_hostname = self._reference_hostname
        super().cert_verify(conn, url, verify, cert)  # type: ignore[no-untyped-call]

    @override
    def init_poolmanager(
        self, connections: int, maxsize: int, block: bool = DEFAULT_POOLBLOCK, **pool_kwargs: Any
    ) -> None:
        # Override this method to make sure the connection pools use the assert_hostname and
        # server_hostname argument for SNI as in
        # https://urllib3.readthedocs.io/en/1.26.15/advanced-usage.html#custom-sni-hostname
        pool_kwargs["assert_hostname"] = self._reference_hostname
        pool_kwargs["server_hostname"] = self._reference_hostname

        # The rest of the method stays the same as in HTTPAdapter
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        # PoolManager takes care already of setting assert_same_host=False in urlopen()
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    @override
    def send(self, request: PreparedRequest, *args: Any, **kwargs: Any) -> Response:
        """Send the request, injecting the Host header for SNI if not already set."""
        # Add Host header for proper SNI implementation as per urllib3 docs
        if "Host" not in request.headers:
            request.headers["Host"] = self._reference_hostname

        return super().send(request, *args, **kwargs)
