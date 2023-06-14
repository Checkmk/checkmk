#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from cmk.gui.painter.v0.painters import host_state_short, service_state_short
from cmk.gui.type_defs import Row


@dataclass
class StateFormatter:
    css: str
    _state_names: Callable[[Row], tuple[str, str]]
    message_template: str

    def state_names(self, row: Row) -> tuple[str, str]:
        return self._state_names(row)


class ServiceStateFormatter(StateFormatter):
    def __init__(self, message_template: str = "{}") -> None:
        super().__init__(
            css="svcstate state{}",
            _state_names=service_state_short,
            message_template=message_template,
        )
        self.css = "svcstate state{}"
        self._state_names = service_state_short
        self.message_template = message_template


def state_map(conf: tuple[str, str] | None, row: Row, formatter: StateFormatter) -> dict[str, str]:
    style = dict(zip(("paint", "status"), conf)) if isinstance(conf, tuple) else {}
    state, status_name = formatter.state_names(row)
    return {
        "css": formatter.css.format(state),
        "msg": formatter.message_template.format(status_name),
        **style,
    }


host_map = partial(
    state_map,
    formatter=StateFormatter(
        "hoststate hstate{}",
        host_state_short,
        "{}",
    ),
)
svc_map = partial(
    state_map,
    formatter=ServiceStateFormatter(),
)
