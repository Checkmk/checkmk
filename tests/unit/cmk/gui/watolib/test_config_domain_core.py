#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pytest_mock import MockerFixture

from cmk.automations.results import ReloadResult, RestartResult
from cmk.gui.config import Config
from cmk.gui.watolib.config_domain_name import ActivationContext
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.hosts_and_folders import ACTIVATION_FOLDER_TREE, FolderTree, make_folder_tree


def _activation_of(tree: FolderTree) -> ActivationContext:
    return ActivationContext({ACTIVATION_FOLDER_TREE: tree})


@pytest.mark.usefixtures("request_context")
def test_activate_bakes_agents_before_the_core_picks_up_the_config(
    mocker: MockerFixture,
) -> None:
    calls: list[str] = []

    def bake(**kwargs: object) -> None:  # noqa: ARG001
        calls.append("bake")

    def restart(*args: object, **kwargs: object) -> RestartResult:  # noqa: ARG001
        calls.append("restart")
        return RestartResult([])

    def reload(*args: object, **kwargs: object) -> ReloadResult:  # noqa: ARG001
        calls.append("reload")
        return ReloadResult([])

    mocker.patch("cmk.gui.watolib.bakery.try_bake_agents_on_activation", side_effect=bake)
    mocker.patch("cmk.gui.watolib.config_domains.restart", side_effect=restart)
    mocker.patch("cmk.gui.watolib.config_domains.reload", side_effect=reload)

    ConfigDomainCore().activate(ctx=_activation_of(make_folder_tree(Config())))

    assert calls[0] == "bake"
    assert calls[1] in ("restart", "reload")


@pytest.mark.usefixtures("request_context")
def test_activate_restarts_the_core_with_the_tree_of_the_activation(
    mocker: MockerFixture,
) -> None:
    """The restart hands the hosts of that tree to the activate changes hooks."""
    handed_trees: list[object] = []

    def restart_or_reload(*_args: object, tree: object, **_kwargs: object) -> RestartResult:
        handed_trees.append(tree)
        return RestartResult([])

    mocker.patch("cmk.gui.watolib.bakery.try_bake_agents_on_activation")
    mocker.patch("cmk.gui.watolib.config_domains.restart", side_effect=restart_or_reload)
    mocker.patch("cmk.gui.watolib.config_domains.reload", side_effect=restart_or_reload)
    tree = make_folder_tree(Config())

    ConfigDomainCore().activate(ctx=_activation_of(tree))

    assert handed_trees == [tree]
