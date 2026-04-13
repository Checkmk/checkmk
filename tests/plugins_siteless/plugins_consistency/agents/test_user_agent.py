#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pkgutil
from collections.abc import Iterable, Sequence
from importlib import import_module
from types import ModuleType

from cmk.ccc import version
from cmk.discover_plugins import discover_families


def _collect_agents() -> Iterable[tuple[str, ModuleType]]:
    for family in discover_families(raise_errors=True):
        try:
            agents_namespace = import_module(f"{family}.agents")
        except ModuleNotFoundError:
            continue

        # This is a little bit hacky. I am not sure it finds everything relevant,
        # nor that it won't choke someday on something that is actually allowed to be in that
        # folder. This is just a heuristic.
        for mod in pkgutil.iter_modules(agents_namespace.__path__):
            full_name = f"{family}.agents.{mod.name}"
            try:
                yield full_name, import_module(full_name)
            except Exception:
                raise
            except BaseException as e:
                assert False, f"Agent plugin tried to exit during import: {full_name}: {e!r}"


def _filter_user_agent_attributes(
    modules: Iterable[tuple[str, ModuleType]],
) -> Sequence[tuple[str, object]]:
    return [(n, m.USER_AGENT) for n, m in modules if hasattr(m, "USER_AGENT")]


def test_expected_agent_and_user_string_count() -> None:
    agent_plugins = tuple(_collect_agents())
    agent_plugins_with_user_agent = {n for n, _ in _filter_user_agent_attributes(agent_plugins)}
    agents_wo_user_agent = {n for n, _ in agent_plugins if n not in agent_plugins_with_user_agent}

    # If this fails, you added an agent plugin without a USER_AGENT attribute.
    # That might be fine if you're not making http requests. Just update the number
    # below then.
    # If you do make requests, however, please consider following the convention.
    assert len(agents_wo_user_agent) == 2


def test_user_agent_strings() -> None:
    """Make sure all user agent strings follow the convention

    "checkmk-agent-<NAME>-<VERSION>"

    """
    assert not {
        name: user_agent
        for name, user_agent in _filter_user_agent_attributes(_collect_agents())
        if not (
            isinstance(user_agent, str)
            and user_agent.startswith("checkmk-agent-")
            and user_agent.endswith(f"-{version.__version__}")
        )
    }
