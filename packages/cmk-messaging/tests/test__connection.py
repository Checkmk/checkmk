#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test that the channel wrapper works as expected"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pika
import pika.adapters.blocking_connection
import pika.channel
import pika.spec
import pytest
from pydantic import BaseModel

from cmk.messaging import AppName, BindingKey, Channel, DeliveryTag, QueueName, RoutingKey


class _ConsumedSuccesfully(RuntimeError):
    """Used to leave the ever-blocking consuming loop"""


class Message(BaseModel):
    """Test model for messages"""

    text: str


@dataclass(frozen=True)
class Queue:
    """Record of a declared queue"""

    name: str
    arguments: Mapping[str, object] | None = None


@dataclass(frozen=True)
class Binding:
    """Record of a binding"""

    exchange: str
    binding_key: str
    queue: str


@dataclass(frozen=True)
class Published:
    """Record of a published message"""

    exchange: str
    routing_key: str
    body: bytes
    properties: pika.BasicProperties


class ChannelTester:
    """Test double for the pika channel"""

    def __init__(self) -> None:
        self.declared_queues: list[Queue] = []
        self.bound_queues: list[Binding] = []
        self.published_messages: list[Published] = []
        self.consumer: (
            Callable[
                [pika.channel.Channel, pika.spec.Basic.Deliver, pika.BasicProperties, bytes], object
            ]
            | None
        ) = None

    def queue_declare(self, queue: str, arguments: Mapping[str, object] | None = None) -> None:
        self.declared_queues.append(Queue(queue, arguments))

    def queue_bind(
        self,
        queue: str,
        exchange: str,
        routing_key: str,
        arguments: None = None,  # noqa: ARG002
    ) -> None:
        self.bound_queues.append(Binding(exchange, routing_key, queue))

    def basic_publish(
        self,
        exchange: str,
        routing_key: str,
        body: bytes,
        properties: pika.BasicProperties | None,
    ) -> None:
        self.published_messages.append(
            Published(exchange, routing_key, body, properties or pika.BasicProperties())
        )

    def basic_consume(
        self,
        queue: str,  # noqa: ARG002
        on_message_callback: Callable[
            [pika.channel.Channel, pika.spec.Basic.Deliver, pika.BasicProperties, bytes],
            object,
        ],
        auto_ack: bool,  # noqa: ARG002
    ) -> None:
        self.consumer = on_message_callback

    def start_consuming(self) -> None:
        assert self.consumer is not None
        for published in self.published_messages:
            # we don't care about the binding and so on. Just call the callback on
            # all stored messages from our test setup.
            self.consumer(
                # TODO: The class hierarchy is simply wrong, ChannelTester must subclass Channel.
                self,  # type: ignore[arg-type]
                pika.spec.Basic.Deliver(delivery_tag=42),
                published.properties,
                published.body,
            )
        # The actual consuming loop would be endless, raise instead.
        # Design your tests to deal with this.

        raise AssertionError("No more messages to consume")

    def basic_ack(self, delivery_tag: int, multiple: bool) -> None:
        pass


def _make_test_channel() -> tuple[Channel[Message], ChannelTester]:
    return Channel(AppName("my-app"), test_channel := ChannelTester(), Message), test_channel


class TestChannel:
    """Test the channel wrapper"""

    @staticmethod
    def test_queue_declare_trivial() -> None:
        """Just declare the default queue and bind to it"""
        channel, test_channel = _make_test_channel()

        channel.queue_declare(QueueName("default"))
        assert test_channel.declared_queues == [Queue("cmk.app.my-app.default")]
        assert test_channel.bound_queues == [
            Binding("cmk.local", "*.my-app.default", "cmk.app.my-app.default")
        ]

    @staticmethod
    def test_queue_declare_ttl() -> None:
        """Declare a queue with ttl"""
        channel, test_channel = _make_test_channel()

        channel.queue_declare(QueueName("Q"), message_ttl=42)
        assert test_channel.declared_queues[0] == Queue(
            "cmk.app.my-app.Q", {"x-message-ttl": 42000}
        )

    @staticmethod
    def test_queue_declare_multiple() -> None:
        channel, test_channel = _make_test_channel()

        channel.queue_declare(
            QueueName("my-queue"),
            [BindingKey("my-first-binding"), BindingKey("my-second-binding.*.yodo")],
        )
        assert test_channel.declared_queues == [Queue("cmk.app.my-app.my-queue")]
        assert test_channel.bound_queues == [
            Binding("cmk.local", "*.my-app.my-first-binding", "cmk.app.my-app.my-queue"),
            Binding("cmk.local", "*.my-app.my-second-binding.*.yodo", "cmk.app.my-app.my-queue"),
        ]

    @staticmethod
    def test_publish_locally() -> None:
        channel, test_channel = _make_test_channel()
        message = Message(text="Hello 🌍")

        channel.publish_locally(message, routing=RoutingKey("subrouting.key"))
        assert test_channel.published_messages == [
            Published(
                "cmk.local",
                "local-site.my-app.subrouting.key",
                b'{"text":"Hello \xf0\x9f\x8c\x8d"}',
                pika.BasicProperties(),
            ),
        ]

    @staticmethod
    def test_publish_for_site() -> None:
        channel, test_channel = _make_test_channel()
        message = Message(text="Hello 🌍")

        channel.publish_for_site("other_site", message, routing=RoutingKey("subrouting.key"))
        assert test_channel.published_messages == [
            Published(
                "cmk.intersite",
                "other_site.my-app.subrouting.key",
                b'{"text":"Hello \xf0\x9f\x8c\x8d"}',
                pika.BasicProperties(),
            ),
        ]

    @staticmethod
    def test_consume_is_called() -> None:
        channel, _test_channel = _make_test_channel()
        message = Message(text="Hello 🌍")

        channel.publish_for_site("other_site", message, routing=RoutingKey("subrouting.key"))

        # make sure that we're called at all
        def _on_message(*_args: object, **_kw: Mapping[str, object]) -> None:
            raise RuntimeError()

        with pytest.raises(RuntimeError):
            channel.consume(QueueName("ignored-by-this-test"), _on_message)

    @staticmethod
    def test_consume_message_model_roundtrip() -> None:
        channel, _test_channel = _make_test_channel()
        message = Message(text="Hello 🌍")

        channel.publish_for_site("other_site", message, routing=RoutingKey("subrouting.key"))

        def _on_message(
            _channel: Channel[Message], _delivery_tag: DeliveryTag, received: Message
        ) -> None:
            assert received == message
            raise _ConsumedSuccesfully()

        with pytest.raises(_ConsumedSuccesfully):
            channel.consume(QueueName("ignored-by-this-test"), _on_message)
