#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper for pika connection classes"""

import socket
import ssl
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Final, Generic, NoReturn, Protocol, Self, TypeVar

import pika
import pika.adapters.blocking_connection
import pika.channel
from pika.exceptions import AMQPConnectionError
from pydantic import BaseModel

from ._config import get_local_port, make_connection_params
from ._constants import APP_PREFIX, INTERSITE_EXCHANGE, LOCAL_EXCHANGE

_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True)
class ConnectionOK:
    """The connection is OK"""


@dataclass(frozen=True)
class ConnectionFailed:
    """The connection is not OK"""

    message: str


@dataclass(frozen=True)
class ConnectionUnknown:
    """The connection state is unknown"""

    message: str


class ChannelP(Protocol):
    """Protocol of the wrapped channel type"""

    def queue_declare(self, queue: str) -> None: ...

    def queue_bind(
        self, queue: str, exchange: str, routing_key: str, arguments: None = None
    ) -> None: ...

    def basic_publish(
        self,
        exchange: str,
        routing_key: str,
        body: bytes,
        properties: pika.BasicProperties | None,
    ) -> None: ...

    def basic_consume(
        self,
        queue: str,
        # For a pure solution, we'd need to have protocol types for the callback arguments as well,
        # but let's keep it simple for now.
        on_message_callback: Callable[
            [pika.channel.Channel, pika.DeliveryMode, pika.BasicProperties, bytes], object
        ],
        auto_ack: bool,
    ) -> None: ...

    def start_consuming(self) -> None: ...


_ChannelT = TypeVar("_ChannelT", bound=ChannelP)


class Channel(Generic[_ModelT]):
    """Wrapper for pika channel.

    Most of the methods are just wrappers around the corresponding pika methods.
    This layer is meant to provide some convenience and get the binding to the app right.
    Feel free to add more methods as needed.

    Most important features:

    - The channel is bound to a specific app
    - Adhere to our binding conventions
    - Send instances of pydantic models instead of raw bytes
    """

    def __init__(
        self,
        app: str,
        pchannel: _ChannelT,
        message_model: type[_ModelT],
    ) -> None:
        super().__init__()
        self.app: Final = app
        self._pchannel: Final = pchannel
        self._model = message_model

    def _make_queue_name(self, suffix: str | None) -> str:
        return f"{APP_PREFIX}.{self.app}" if suffix is None else f"{APP_PREFIX}.{self.app}.{suffix}"

    def _make_binding_key(self, suffix: str | None) -> str:
        return f"*.{self.app}" if suffix is None else f"*.{self.app}.{suffix}"

    def _make_routing_key(self, site: str, routing_sub_key: str | None) -> str:
        return (
            f"{site}.{self.app}"
            if routing_sub_key is None
            else f"{site}.{self.app}.{routing_sub_key}"
        )

    def queue_declare(
        self,
        queue: str | None = None,
        bindings: Sequence[str | None] = (None,),
    ) -> None:
        """
        Bind a queue to the local exchange with the given queue and bindings.

        Args:
            queue: The queue to bind to. If None, "cmk.app.{app}" name is used,
               otherwise "cmk.app.{app}.{queue}".
            bindings: The bindings to use. For every provided element we add the binding
               "*.{app}" if the element is None, otherwise "*.{app}.{binding}".

        You can omit all arguments, but you _must_ bind in order to consume messages.
        """
        full_queue_name = self._make_queue_name(queue)
        self._pchannel.queue_declare(queue=full_queue_name)
        for binding in bindings:
            self._pchannel.queue_bind(
                exchange=LOCAL_EXCHANGE,
                queue=full_queue_name,
                routing_key=self._make_binding_key(binding),
            )

    def publish_locally(
        self,
        message: _ModelT,
        *,
        properties: pika.BasicProperties | None = None,
        routing: str | None = None,
    ) -> None:
        self._pchannel.basic_publish(
            exchange=LOCAL_EXCHANGE,
            routing_key=self._make_routing_key("local-site", routing),
            body=message.model_dump_json().encode("utf-8"),
            properties=properties,
        )

    def publish_for_site(
        self,
        site: str,
        message: _ModelT,
        *,
        properties: pika.BasicProperties = pika.BasicProperties(),
        routing: str | None = None,
    ) -> None:
        self._pchannel.basic_publish(
            exchange=INTERSITE_EXCHANGE,
            routing_key=self._make_routing_key(site, routing),
            body=message.model_dump_json().encode("utf-8"),
            properties=properties,
        )

    def consume(
        self,
        callback: Callable[[Self, _ModelT], object],
        *,
        auto_ack: bool = False,
        queue: str | None = None,
    ) -> NoReturn:
        """Block forever and call the callback for every message received.

        This is a combination of pika's `basic_consume` and `start_consuming` methods.
        Currently there's no need to expose these methods separately.
        """

        def _on_message(
            _channel: pika.channel.Channel,
            _method: pika.DeliveryMode,
            _properties: pika.BasicProperties,
            body: bytes,
        ) -> None:
            callback(self, self._model.model_validate_json(body.decode("utf-8")))

        self._pchannel.basic_consume(
            queue=self._make_queue_name(queue),
            on_message_callback=_on_message,
            auto_ack=auto_ack,
        )
        self._pchannel.start_consuming()

        raise RuntimeError("start_consuming() should never return")


class Connection:
    """Connection to the local message broker

    Instances should be reused, as establishing the connection is comperatively expensive.
    Most of the methods are just wrappers around the corresponding pika methods.
    Feel free to add more methods as needed.

    We want to return our version of a channel, though.

    Basic example:

    To publish a message:

    ```python

    with Connection("myapp", Path("/omd/sites/mysite")) as conn:
        channel = conn.channel(MyMessageModel)
        channel.publish_for_site("other_site", my_message_instance)

    ```

    To consume messages:

    ```python

    with Connection("myapp", Path("/omd/sites/mysite")) as conn:
        channel = conn.channel(MyMessageModel)
        channel.queue_declare()  # default queue + bindings
        channel.consume(my_message_handler_callback)

    ```
    """

    def __init__(self, app: str, omd_root: Path) -> None:
        """Create a connection for a specific app"""
        if not app:
            raise ValueError(app)
        self.app: Final = app
        self._omd_root = omd_root
        self._pconnection = pika.BlockingConnection(
            make_connection_params(omd_root, "localhost", get_local_port())
        )

    def channel(self, model: type[_ModelT]) -> Channel[_ModelT]:
        return Channel(self.app, self._pconnection.channel(), model)

    def __enter__(self) -> Self:
        self._pconnection.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self._pconnection.__exit__(exc_type, value, traceback)


def check_remote_connection(
    omd_root: Path, server: str, port: int
) -> ConnectionOK | ConnectionFailed:
    """
    Check if a connection to a remote message broker can be established

    Args:
        omd_root: The OMD root path of the site to connect from
        server: Hostname or IP Address to connect to
        port: The message broker port to connect to
    """

    try:
        with pika.BlockingConnection(make_connection_params(omd_root, server, port)):
            return ConnectionOK()
    except (RuntimeError, socket.gaierror, ssl.SSLError, AMQPConnectionError) as exc:
        return ConnectionFailed(str(exc))
