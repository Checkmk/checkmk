#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.postfix_mailq import (
    check_postfix_mailq,
    DEFAULT_ITEM_NAME,
    discovery_postfix_mailq,
    parse_postfix_mailq,
    PostfixMailQueue,
    Section,
)


def test_postfix_variant_single_mailq_total_requests() -> None:
    old_variant_data = [
        ["8BITMIME", "(Deferred:", "Connection", "refused", "by", "mail.gargl.com.)"],
        ["", "<franz@gargle.com>"],
        ["q1L4ovDO002485", "3176", "Tue", "Feb", "21", "05:50", "MAILER-DAEMON"],
        ["(Deferred:", "451", "Try", "again", "later)"],
        ["<wrdlpfrmpft@karl-valentin.com>"],
        ["Total", "requests:", "2"],
    ]
    _result = parse_postfix_mailq(old_variant_data)
    assert isinstance(_result, dict)
    assert (
        PostfixMailQueue(
            name="mail",
            size=0,
            length=2,
        )
        in _result[DEFAULT_ITEM_NAME]
    )
    assert len(_result) == 1
    assert len(_result[DEFAULT_ITEM_NAME]) == 1


def test_postfix_variant_single_mailq() -> None:
    single_instance_data = [
        ["-Queue ID-", "--Size--", "----Arrival Time----", "-Sender/Recipient-------"],
        ["CA29995448EB", "4638", "Fri Jul  2 14:39:01", "nagios"],
        ["", "", "", "donatehosts@mathias-kettner.de"],
        ["E085095448EC", "240", "Fri Jul  2 14:40:01", "root"],
        ["", "", "", "lm@mathias-kettner.de"],
        ["--", "9", "Kbytes", "in", "3", "Requests."],
    ]
    single_instance_data_result = parse_postfix_mailq(single_instance_data)
    assert isinstance(single_instance_data_result, dict)
    assert (
        PostfixMailQueue(
            name="mail",
            size=9216,
            length=3,
        )
        in single_instance_data_result[DEFAULT_ITEM_NAME]
    )
    assert len(single_instance_data_result) == 1
    assert len(single_instance_data_result[DEFAULT_ITEM_NAME]) == 1


def test_parse_multiple_queues_postfix_mailq() -> None:
    multi_queues_data = [
        ["QUEUE_deferred", "128", "2"],
        ["QUEUE_active", "256", "4"],
        ["QUEUE_other", "512", "6"],
    ]
    multi_queues_data_result = parse_postfix_mailq(multi_queues_data)
    assert isinstance(multi_queues_data_result, dict)
    assert (
        PostfixMailQueue(
            name="deferred",
            size=128,
            length=2,
        )
        in multi_queues_data_result[DEFAULT_ITEM_NAME]
    )
    assert (
        PostfixMailQueue(
            name="active",
            size=256,
            length=4,
        )
        in multi_queues_data_result[DEFAULT_ITEM_NAME]
    )
    assert (
        PostfixMailQueue(
            name="other",
            size=512,
            length=6,
        )
        in multi_queues_data_result[DEFAULT_ITEM_NAME]
    )
    assert len(multi_queues_data_result) == 1
    assert len(multi_queues_data_result[DEFAULT_ITEM_NAME]) == 3


def test_parse_multi_instance_postfix_mailq() -> None:
    multi_instance_data = [
        ["[[[/etc/postfix-external]]]"],
        ["QUEUE_deferred", "128", "2"],
        ["QUEUE_active", "256", "4"],
        ["[[[/etc/postfix-internal]]]"],
        ["QUEUE_deferred", "512", "6"],
        ["QUEUE_active", "1024", "8"],
    ]
    multi_instance_data_result = parse_postfix_mailq(multi_instance_data)
    assert isinstance(multi_instance_data_result, dict)
    assert (
        PostfixMailQueue(
            name="deferred",
            size=128,
            length=2,
        )
        in multi_instance_data_result["/etc/postfix-external"]
    )
    assert (
        PostfixMailQueue(
            name="active",
            size=256,
            length=4,
        )
        in multi_instance_data_result["/etc/postfix-external"]
    )
    assert (
        PostfixMailQueue(
            name="deferred",
            size=512,
            length=6,
        )
        in multi_instance_data_result["/etc/postfix-internal"]
    )
    assert (
        PostfixMailQueue(
            name="active",
            size=1024,
            length=8,
        )
        in multi_instance_data_result["/etc/postfix-internal"]
    )
    assert len(multi_instance_data_result) == 2
    assert len(multi_instance_data_result["/etc/postfix-internal"]) == 2
    assert len(multi_instance_data_result["/etc/postfix-external"]) == 2


def test_discovery_postfix_mailq() -> None:
    section: Section = {
        DEFAULT_ITEM_NAME: [
            PostfixMailQueue(
                name="active",
                size=1024,
                length=8,
            ),
            PostfixMailQueue(
                name="deferred",
                size=512,
                length=5,
            ),
        ]
    }
    result = list(discovery_postfix_mailq(section))
    assert result == [Service(item=DEFAULT_ITEM_NAME)]


def test_check_postfix_mailq() -> None:
    item = "deferred"
    params = {"deferred": (10, 20)}
    parsed: Section = {
        "deferred": [PostfixMailQueue(name="deferred", size=2048, length=1)],
    }
    result = list(check_postfix_mailq(item, params, parsed))
    assert len(result) == 4
    assert isinstance(result[0], Result)
    assert isinstance(result[1], Metric)
    assert isinstance(result[2], Result)
    assert isinstance(result[3], Metric)

    assert result[0] == Result(state=State.OK, summary="deferred queue length: 1")
    assert result[1] == Metric("length", 1, levels=(10.0, 20.0))
    assert result[2] == Result(state=State.OK, summary="deferred queue size: 2.00 KiB")
    assert result[3] == Metric("size", 2048)
