#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels
from cmk.agent_based.v2 import render

NULLMAILER_MAILQ_DEFAULT_LEVELS = {
    "deferred": (10, 20),
    "failed": (1, 1),
}


class Queue(typing.NamedTuple):
    size: int
    length: int
    name: str


def parse_nullmailer_mailq(info):
    def name(line: str) -> str:
        return line[2] if len(line) == 3 else "deferred"

    return [Queue(size=int(line[0]), length=int(line[1]), name=name(line)) for line in info]


def check_single_queue(queue: Queue, levels_length: tuple[int, int]) -> Iterable[tuple]:
    make_metric = queue.name == "deferred"

    yield check_levels(
        queue.length,
        "length" if make_metric else None,
        levels_length,
        human_readable_func=lambda x: "%d" % x,
        infoname=queue.name.capitalize(),
        unit="mails",
    )

    yield check_levels(
        queue.size,
        "size" if make_metric else None,
        None,
        human_readable_func=render.bytes,
        infoname="Size",
    )


def check_nullmailer_mailq(_no_item, params, parsed):
    if not isinstance(params, dict):
        params = {
            "deferred": params,
        }

    for queue in parsed:
        yield from check_single_queue(queue, params.get(queue.name))
