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
import pytest
from pydantic import BaseModel

from cmk.messaging import Channel


class _ConsumedSuccesfully(RuntimeError):
    """Used to leave the ever-blocking consuming loop"""


class Message(BaseModel):
    """Test model for messages"""

    text: str


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
        self.declared_queues: list[str] = []
        self.bound_queues: list[Binding] = []
        self.published_messages: list[Published] = []
        self.consumer: (
            Callable[[pika.channel.Channel, pika.DeliveryMode, pika.BasicProperties, bytes], object]
            | None
        ) = None

    def queue_declare(self, queue: str) -> None:
        self.declared_queues.append(queue)

    def queue_bind(
        self,
        queue: str,
        exchange: str,
        routing_key: str,
        arguments: None = None,  # pylint: disable=unused-argument
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
        queue: str,  # pylint: disable=unused-argument
        on_message_callback: Callable[
            [pika.channel.Channel, pika.DeliveryMode, pika.BasicProperties, bytes],
            object,
        ],
        auto_ack: bool,  # pylint: disable=unused-argument
    ) -> None:
        self.consumer = on_message_callback

    def start_consuming(self) -> None:
        assert self.consumer is not None
        for published in self.published_messages:
            # we don't care about the binding and so on. Just call the callback on
            # all stored messages from our test setup.
            self.consumer(
                None,  # type: ignore[arg-type] # don't create a Channel just to ignore it
                pika.DeliveryMode.Persistent,
                published.properties,
                published.body,
            )
        # The actual consuming loop would be endless, raise instead.
        # Design your tests to deal with this.

        raise AssertionError("No more messages to consume")


def _make_test_channel() -> tuple[Channel[Message], ChannelTester]:
    return Channel("my-app", test_channel := ChannelTester(), Message), test_channel


class TestChannel:
    """Test the channel wrapper"""

    @staticmethod
    def test_queue_declare_trivial() -> None:
        """Just declare the default queue and bind to it"""
        channel, test_channel = _make_test_channel()

        channel.queue_declare()
        assert test_channel.declared_queues == ["cmk.app.my-app"]
        assert test_channel.bound_queues == [Binding("cmk.local", "*.my-app", "cmk.app.my-app")]

    @staticmethod
    def test_queue_declare_multiple() -> None:
        channel, test_channel = _make_test_channel()

        channel.queue_declare("my-queue", ["my-first-binding", "my-second-binding.*.yodo"])
        assert test_channel.declared_queues == ["cmk.app.my-app.my-queue"]
        assert test_channel.bound_queues == [
            Binding("cmk.local", "*.my-app.my-first-binding", "cmk.app.my-app.my-queue"),
            Binding("cmk.local", "*.my-app.my-second-binding.*.yodo", "cmk.app.my-app.my-queue"),
        ]

    @staticmethod
    def test_publish_locally() -> None:
        channel, test_channel = _make_test_channel()
        message = Message(text="Hello 🌍")

        channel.publish_locally(message, routing="subrouting.key")
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

        channel.publish_for_site("other_site", message, routing="subrouting.key")
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

        channel.publish_for_site("other_site", message, routing="subrouting.key")

        # make sure that we're called at all
        def _on_message(*args: object, **kw: Mapping[str, object]) -> None:
            raise RuntimeError()

        with pytest.raises(RuntimeError):
            channel.consume(_on_message)

    @staticmethod
    def test_consume_message_model_roundtrip() -> None:
        channel, _test_channel = _make_test_channel()
        message = Message(text="Hello 🌍")

        channel.publish_for_site("other_site", message, routing="subrouting.key")

        def _on_message(_channel: Channel[Message], received: Message) -> None:
            assert received == message
            raise _ConsumedSuccesfully()

        with pytest.raises(_ConsumedSuccesfully):
            channel.consume(_on_message)
