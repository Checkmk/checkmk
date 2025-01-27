#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper for pika connection classes"""

import socket
import ssl
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Final, Generic, NoReturn, Protocol, Self, TypeVar

import pika
import pika.adapters.blocking_connection
import pika.channel
import pika.spec
from pika.exceptions import AMQPConnectionError, StreamLostError
from pydantic import BaseModel

from ._config import get_local_port, make_connection_params
from ._constants import APP_PREFIX, INTERSITE_EXCHANGE, LOCAL_EXCHANGE


@dataclass(frozen=True)
class AppName:
    """The application name
    Any string that does not contain '.', '#' or '*'.
    It is used in routing and binding keys, for which these are of
    special significance.
    """

    value: str

    def __post_init__(self) -> None:
        if {"#", ".", "*"}.intersection(self.value) or not self.value:
            raise ValueError(self.value)


@dataclass(frozen=True)
class QueueName:
    """The queue name"""

    # Queue names can be up to 255 bytes of UTF-8 characters.
    # We don't enforce this here, because we will construct the full queue name
    # with the app name, this queue name and some constant parts.
    value: str


@dataclass(frozen=True)
class RoutingKey:
    """The routing sub key

    Any string that does not contain '#' or '*'.
    These are of special significance for the _binding_ key.
    """

    value: str

    def __post_init__(self) -> None:
        if {"#", "*"}.intersection(self.value) or not self.value:
            raise ValueError(self.value)


@dataclass(frozen=True)
class BindingKey:
    """The binding key"""

    value: str


class CMKConnectionError(RuntimeError):
    pass


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

    def queue_declare(
        self, queue: str, *, arguments: Mapping[str, object] | None = None
    ) -> None: ...

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
            [pika.channel.Channel, pika.spec.Basic.Deliver, pika.BasicProperties, bytes], object
        ],
        auto_ack: bool,
    ) -> None: ...

    def start_consuming(self) -> None: ...

    def basic_ack(self, delivery_tag: int, multiple: bool) -> None: ...


_ChannelT = TypeVar("_ChannelT", bound=ChannelP)


class DeliveryTag(int): ...


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
        app_name: AppName,
        pchannel: _ChannelT,
        message_model: type[_ModelT],
    ) -> None:
        super().__init__()
        self.app_name: Final = app_name
        self._pchannel: Final = pchannel
        self._model = message_model

    def _make_queue_name(self, suffix: QueueName) -> str:
        return f"{APP_PREFIX}.{self.app_name.value}.{suffix.value}"

    def _make_binding_key(self, suffix: BindingKey) -> str:
        return f"*.{self.app_name.value}.{suffix.value}"

    def _make_routing_key(self, site: str, routing_sub_key: RoutingKey) -> str:
        return f"{site}.{self.app_name.value}.{routing_sub_key.value}"

    def queue_declare(
        self,
        queue: QueueName,
        bindings: Sequence[BindingKey] | None = None,
        message_ttl: int | None = None,
    ) -> None:
        """
        Bind a queue to the local exchange with the given queue and bindings.

        Args:
            queue: The queue to bind to. Full queue name will be "cmk.app.{app}.{queue}".
            bindings: The bindings to use. For every provided element we add the binding
                "*.{app}.{binding}". Defaults to None, in which case we bind with "*.{app}.{queue}".

        You _must_ bind in order to consume messages.
        """
        bindings = bindings or [BindingKey(queue.value)]
        full_queue_name = self._make_queue_name(queue)
        try:
            self._pchannel.queue_declare(
                queue=full_queue_name,
                arguments=None if message_ttl is None else {"x-message-ttl": message_ttl * 1000},
            )
            for binding in bindings:
                self._pchannel.queue_bind(
                    exchange=LOCAL_EXCHANGE,
                    queue=full_queue_name,
                    routing_key=self._make_binding_key(binding),
                )
        except AMQPConnectionError as e:
            # pika handles exceptions weirdly. We need repr, in order to see something.
            raise CMKConnectionError(repr(e)) from e

    def publish_locally(
        self,
        message: _ModelT,
        routing: RoutingKey,
        properties: pika.BasicProperties | None = None,
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
        routing: RoutingKey,
        properties: pika.BasicProperties = pika.BasicProperties(),
    ) -> None:
        try:
            self._pchannel.basic_publish(
                exchange=INTERSITE_EXCHANGE,
                routing_key=self._make_routing_key(site, routing),
                body=message.model_dump_json().encode("utf-8"),
                properties=properties,
            )
        except AMQPConnectionError as e:
            # pika handles exceptions weirdly. We need repr, in order to see something.
            raise CMKConnectionError(repr(e)) from e

    def consume(
        self,
        queue: QueueName,
        callback: Callable[[Self, DeliveryTag, _ModelT], object],
        *,
        auto_ack: bool = False,
    ) -> NoReturn:
        """Block forever and call the callback for every message received.

        This is a combination of pika's `basic_consume` and `start_consuming` methods.
        Currently there's no need to expose these methods separately.
        """

        def _on_message(
            _channel: pika.channel.Channel,
            method: pika.spec.Basic.Deliver,
            _properties: pika.spec.BasicProperties,
            body: bytes,
        ) -> None:
            callback(
                self,
                DeliveryTag(method.delivery_tag),
                self._model.model_validate_json(body.decode("utf-8")),
            )

        self._pchannel.basic_consume(
            queue=self._make_queue_name(queue),
            on_message_callback=_on_message,
            auto_ack=auto_ack,
        )
        try:
            self._pchannel.start_consuming()
        except (AMQPConnectionError, StreamLostError) as e:
            raise CMKConnectionError from e

        raise RuntimeError("start_consuming() should never return")

    def acknowledge(self, delivery_tag: DeliveryTag) -> None:
        self._pchannel.basic_ack(delivery_tag=delivery_tag, multiple=False)


class Connection:
    """Connection to the local message broker

    Instances should be reused, as establishing the connection is comparatively expensive.
    Most of the methods are just wrappers around the corresponding pika methods.
    Feel free to add more methods as needed.

    We want to return our version of a channel, though.

    Basic example:

    To publish a message:

    ```python

    with Connection(AppName("myapp"), Path("/omd/sites/mysite"), "mysite") as conn:
        channel = conn.channel(MyMessageModel)
        channel.publish_for_site("other_site", my_message_instance, RoutintKey("my_routing"))

    ```

    To consume messages:

    ```python

    with Connection(AppName("myapp"), Path("/omd/sites/mysite"), "mysite") as conn:
        channel = conn.channel(MyMessageModel)
        channel.queue_declare(QueueName("default"))  # includes default binding
        channel.consume(my_message_handler_callback)

    ```

    To name distinguish between different app connections, you can additionally provide a connection
     name:

    ```python

    with Connection(AppName("myapp"), Path("/omd/sites/mysite"), , "mysite", "my-connection") as conn:
        ...

    """

    def __init__(
        self, app: AppName, omd_root: Path, omd_site: str, connection_name: str | None = None
    ) -> None:
        """Create a connection for a specific app"""
        self.app: Final = app
        self._omd_root = omd_root
        try:
            self._pconnection = pika.BlockingConnection(
                make_connection_params(
                    omd_root,
                    "localhost",
                    get_local_port(),
                    omd_site,
                    connection_name if connection_name else app.value,
                )
            )
        except AMQPConnectionError as e:
            # pika handles exceptions weirdly. We need repr, in order to see something.
            raise CMKConnectionError(repr(e)) from e

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
        try:
            return self._pconnection.__exit__(exc_type, value, traceback)
        except AMQPConnectionError as e:
            # pika handles exceptions weirdly. We need repr, in order to see something.
            raise CMKConnectionError(repr(e)) from e
        finally:
            # the pika connections __exit__ will swallow these :-(
            if isinstance(value, SystemExit):
                raise value


def check_remote_connection(
    omd_root: Path, server: str, port: int, omd_site: str
) -> ConnectionOK | ConnectionFailed:
    """
    Check if a connection to a remote message broker can be established

    Args:
        omd_root: The OMD root path of the site to connect from
        server: Hostname or IP Address to connect to
        port: The message broker port to connect to
        omd_site: The site id to connect to
    """

    try:
        with pika.BlockingConnection(
            make_connection_params(
                omd_root, server, port, omd_site, f"check-connection-from-{omd_root.name}"
            )
        ):
            return ConnectionOK()
    except AMQPConnectionError as exc:
        return (
            ConnectionFailed("Connection refused")
            if "connection refused" in repr(exc).lower()
            else ConnectionFailed(str(exc))
        )
    except ssl.SSLError as exc:
        msg = repr(exc).lower()
        if "hostname mismatch" in msg:
            return ConnectionFailed(
                "Hostname mismatch."
                " You are probably connecting to the wrong site."
                f" I tried port {port}."
            )
        if "self-signed" in msg:
            return ConnectionFailed(
                "Target broker uses self-signed certificate."
                " You might be connecting to the wrong site."
                f" I tried port {port}."
            )
        if "certificate verify failed" in msg:
            return ConnectionFailed("Certificate verify failed")

        return ConnectionFailed(str(exc))

    except (socket.gaierror, RuntimeError) as exc:
        return ConnectionFailed(str(exc))
