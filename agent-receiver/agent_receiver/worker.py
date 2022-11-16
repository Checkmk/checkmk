#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=too-many-branches,no-else-break

from ssl import SSLObject
from typing import Optional

from uvicorn.protocols.http.h11_impl import (  # type: ignore[import]
    asyncio,
    h11,
    H11Protocol,
    HIGH_WATER_LIMIT,
    RequestResponseCycle,
    service_unavailable,
    unquote,
)
from uvicorn.workers import UvicornWorker  # type: ignore[import]


def _extract_client_cert_cn(ssl_object: Optional[SSLObject]) -> Optional[str]:
    if ssl_object is None:
        return None
    try:
        client_cert = ssl_object.getpeercert()
    except ValueError:
        return None
    if client_cert is None:
        return None

    for distinguished_name in client_cert.get("subject", ()):
        if cn := dict(dn for dn in distinguished_name if isinstance(dn, tuple)).get("commonName"):
            return cn

    return None


class _ClientCertProtocol(H11Protocol):
    # copied from uvicorn.protocols.http.h11_impl.H11Protocol
    def handle_events(self):
        while True:
            try:
                event = self.conn.next_event()
            except h11.RemoteProtocolError as exc:
                msg = "Invalid HTTP request received."
                self.logger.warning(msg, exc_info=exc)
                self.transport.close()
                return
            event_type = type(event)

            if event_type is h11.NEED_DATA:
                break

            elif event_type is h11.PAUSED:
                # This case can occur in HTTP pipelining, so we need to
                # stop reading any more data, and ensure that at the end
                # of the active request/response cycle we handle any
                # events that have been buffered up.
                self.flow.pause_reading()
                break

            elif event_type is h11.Request:
                self.headers = [(key.lower(), value) for key, value in event.headers]

                # ==================================================================================
                # ==================================================================================
                # OUR CUSTOM EXTENSION

                client_cn = _extract_client_cert_cn(self.transport.get_extra_info("ssl_object"))
                self.headers = [
                    (
                        b"verified-uuid",
                        client_cn.encode()
                        if client_cn is not None
                        else b"missing: no client certificate provided",
                    ),
                    *self.headers,
                ]

                # ==================================================================================
                # ==================================================================================

                raw_path, _, query_string = event.target.partition(b"?")
                self.scope = {
                    "type": "http",
                    "asgi": {
                        "version": self.config.asgi_version,
                        "spec_version": "2.1",
                    },
                    "http_version": event.http_version.decode("ascii"),
                    "server": self.server,
                    "client": self.client,
                    "scheme": self.scheme,
                    "method": event.method.decode("ascii"),
                    "root_path": self.root_path,
                    "path": unquote(raw_path.decode("ascii")),
                    "raw_path": raw_path,
                    "query_string": query_string,
                    "headers": self.headers,
                }

                for name, value in self.headers:
                    if name == b"connection":
                        tokens = [token.lower().strip() for token in value.split(b",")]
                        if b"upgrade" in tokens:
                            self.handle_upgrade(event)
                            return

                # Handle 503 responses when 'limit_concurrency' is exceeded.
                if self.limit_concurrency is not None and (
                    len(self.connections) >= self.limit_concurrency
                    or len(self.tasks) >= self.limit_concurrency
                ):
                    app = service_unavailable
                    message = "Exceeded concurrency limit."
                    self.logger.warning(message)
                else:
                    app = self.app

                self.cycle = RequestResponseCycle(
                    scope=self.scope,
                    conn=self.conn,
                    transport=self.transport,
                    flow=self.flow,
                    logger=self.logger,
                    access_logger=self.access_logger,
                    access_log=self.access_log,
                    default_headers=self.default_headers,
                    message_event=asyncio.Event(),
                    on_response=self.on_response_complete,
                )
                task = self.loop.create_task(self.cycle.run_asgi(app))
                task.add_done_callback(self.tasks.discard)
                self.tasks.add(task)

            elif event_type is h11.Data:
                if self.conn.our_state is h11.DONE:
                    continue
                self.cycle.body += event.data
                if len(self.cycle.body) > HIGH_WATER_LIMIT:
                    self.flow.pause_reading()
                self.cycle.message_event.set()

            elif event_type is h11.EndOfMessage:
                if self.conn.our_state is h11.DONE:
                    self.transport.resume_reading()
                    self.conn.start_next_cycle()
                    continue
                self.cycle.more_body = False
                self.cycle.message_event.set()


class ClientCertWorker(UvicornWorker):
    CONFIG_KWARGS = {
        **UvicornWorker.CONFIG_KWARGS,
        "http": _ClientCertProtocol,
    }
