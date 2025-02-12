#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import asyncio
from ssl import SSLObject
from typing import override
from urllib.parse import unquote

import h11
from uvicorn.protocols.http.flow_control import HIGH_WATER_LIMIT, service_unavailable
from uvicorn.protocols.http.h11_impl import H11Protocol, RequestResponseCycle
from uvicorn_worker import UvicornWorker


def _extract_client_cert_cn(ssl_object: SSLObject | None) -> str | None:
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
    @override
    def handle_events(self) -> None:
        while True:
            try:
                event = self.conn.next_event()
            except h11.RemoteProtocolError:
                msg = "Invalid HTTP request received."
                self.logger.warning(msg)
                self.send_400_response(msg)
                return

            if event is h11.NEED_DATA:
                break

            elif event is h11.PAUSED:
                # This case can occur in HTTP pipelining, so we need to
                # stop reading any more data, and ensure that at the end
                # of the active request/response cycle we handle any
                # events that have been buffered up.
                self.flow.pause_reading()
                break

            elif isinstance(event, h11.Request):
                self.headers = [(key.lower(), value) for key, value in event.headers]

                # ==================================================================================
                # ==================================================================================
                # OUR CUSTOM EXTENSION

                client_cn = _extract_client_cert_cn(self.transport.get_extra_info("ssl_object"))
                self.headers = [
                    (
                        b"verified-uuid",
                        (
                            client_cn.encode()
                            if client_cn is not None
                            else b"missing: no client certificate provided"
                        ),
                    ),
                    *self.headers,
                ]

                # ==================================================================================
                # ==================================================================================

                raw_path, _, query_string = event.target.partition(b"?")
                path = unquote(raw_path.decode("ascii"))
                full_path = self.root_path + path
                full_raw_path = self.root_path.encode("ascii") + raw_path
                self.scope = {
                    "type": "http",
                    "asgi": {"version": self.config.asgi_version, "spec_version": "2.3"},
                    "http_version": event.http_version.decode("ascii"),
                    "server": self.server,
                    "client": self.client,
                    "scheme": self.scheme,  # type: ignore[typeddict-item]
                    "method": event.method.decode("ascii"),
                    "root_path": self.root_path,
                    "path": full_path,
                    "raw_path": full_raw_path,
                    "query_string": query_string,
                    "headers": self.headers,
                    "state": self.app_state.copy(),
                }
                if self._should_upgrade():
                    self.handle_websocket_upgrade(event)
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

                # When starting to process a request, disable the keep-alive
                # timeout. Normally we disable this when receiving data from
                # client and set back when finishing processing its request.
                # However, for pipelined requests processing finishes after
                # already receiving the next request and thus the timer may
                # be set here, which we don't want.
                self._unset_keepalive_if_required()

                self.cycle = RequestResponseCycle(
                    scope=self.scope,
                    conn=self.conn,
                    transport=self.transport,
                    flow=self.flow,
                    logger=self.logger,
                    access_logger=self.access_logger,
                    access_log=self.access_log,
                    default_headers=self.server_state.default_headers,
                    message_event=asyncio.Event(),
                    on_response=self.on_response_complete,
                )
                task = self.loop.create_task(self.cycle.run_asgi(app))
                task.add_done_callback(self.tasks.discard)
                self.tasks.add(task)

            elif isinstance(event, h11.Data):
                if self.conn.our_state is h11.DONE:
                    continue
                self.cycle.body += event.data
                if len(self.cycle.body) > HIGH_WATER_LIMIT:
                    self.flow.pause_reading()
                self.cycle.message_event.set()

            elif isinstance(event, h11.EndOfMessage):
                if self.conn.our_state is h11.DONE:
                    self.transport.resume_reading()
                    self.conn.start_next_cycle()
                    continue
                self.cycle.more_body = False
                self.cycle.message_event.set()
                if self.conn.their_state == h11.MUST_CLOSE:
                    break


class ClientCertWorker(UvicornWorker):
    CONFIG_KWARGS = {
        **UvicornWorker.CONFIG_KWARGS,
        "http": _ClientCertProtocol,
    }
