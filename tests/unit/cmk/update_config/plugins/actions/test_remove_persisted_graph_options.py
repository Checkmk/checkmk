#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger

import pytest

from cmk.gui.graphing._graph_specification import GraphDataRange
from cmk.gui.logged_in import user

from cmk.update_config.plugins.actions.remove_persisted_graph_options import (
    RemovePersistedGraphOptions,
)


def _persist_graph_options() -> None:
    user.save_file(
        "graph_range",
        GraphDataRange(
            time_range=(1, 2),
            step=1,
        ).model_dump_json(),
    )
    user.save_file("graph_size", (10, 20))


def _load_graph_options() -> tuple[object, object]:
    return (
        user.load_file("graph_range", None),
        user.load_file("graph_size", None),
    )


@pytest.mark.usefixtures("with_user_login")
def test_first_execution() -> None:
    _persist_graph_options()
    update_action_state: dict[str, str] = {}

    RemovePersistedGraphOptions(
        name="name",
        title="title",
        sort_index=1,
    )(
        getLogger(),
        update_action_state,
    )

    assert not any(_load_graph_options())
    assert update_action_state[RemovePersistedGraphOptions._KEY] == "True"


@pytest.mark.usefixtures("with_user_login")
def test_noop_if_already_executed() -> None:
    _persist_graph_options()
    update_action_state = {RemovePersistedGraphOptions._KEY: "True"}

    RemovePersistedGraphOptions(
        name="name",
        title="title",
        sort_index=1,
    )(
        getLogger(),
        update_action_state,
    )

    assert all(_load_graph_options())
    assert update_action_state[RemovePersistedGraphOptions._KEY] == "True"
