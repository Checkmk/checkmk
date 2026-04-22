#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import SDNodeName, SDPath
from cmk.utils.user import UserId

from cmk.gui.type_defs import HTTPVariables, LinkFromSpec, Rows, SingleInfos, Visual
from cmk.gui.views.visual_type import _compute_link_from_result


def _make_visual(link_from: LinkFromSpec) -> Visual:
    return Visual(
        owner=UserId("testuser"),
        name="test_visual",
        context={},
        single_infos=[],
        add_context_to_title=False,
        title="Test visual",
        description="",
        topic="",
        sort_index=0,
        is_show_more=False,
        icon=None,
        hidden=False,
        hidebutton=False,
        public=False,
        packaged=False,
        link_from=link_from,
        megamenu_search_terms=[],
    )


def _path(*names: str) -> SDPath:
    return tuple(SDNodeName(n) for n in names)


def _base_returns_true(
    single_infos: SingleInfos, rows: Rows, visual: Visual, context_vars: HTTPVariables
) -> bool:
    return True


def _base_checks_rows(
    single_infos: SingleInfos, rows: Rows, visual: Visual, context_vars: HTTPVariables
) -> bool:
    return bool(rows)


def _tree_found(hostname: HostName, site_id: SiteId, path: SDPath | None, is_history: bool) -> bool:
    return path is not None


def _tree_not_found(
    hostname: HostName, site_id: SiteId, path: SDPath | None, is_history: bool
) -> bool:
    return False


def test_empty_link_from_always_shows() -> None:
    assert (
        _compute_link_from_result(
            [],
            [],
            _make_visual({}),
            [],
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is True
    )


def test_non_inventory_link_from_delegates_to_base_with_matching_rows() -> None:
    row: dict[str, object] = {"host_labels": {}, "host_label_sources": {}}
    visual = _make_visual({"single_infos": ["host"], "host_labels": {}})
    assert (
        _compute_link_from_result(
            ["host"],
            [row],
            visual,
            [],
            base_link_from=_base_checks_rows,
            has_inventory_tree=_tree_found,
        )
        is True
    )


def test_non_inventory_link_from_delegates_to_base_with_empty_rows() -> None:
    visual = _make_visual({"single_infos": ["host"], "host_labels": {}})
    assert (
        _compute_link_from_result(
            ["host"],
            [],
            visual,
            [],
            base_link_from=_base_checks_rows,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_inventory_tree_link_empty_rows() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware", "cpu")})
    context_vars: HTTPVariables = [("host", "myhost"), ("site", "mysite")]
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            context_vars,
            base_link_from=_base_checks_rows,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_inventory_tree_history_link_empty_rows() -> None:
    visual = _make_visual({"has_inventory_tree_history": _path("hardware")})
    context_vars: HTTPVariables = [("host", "myhost"), ("site", "mysite")]
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            context_vars,
            base_link_from=_base_checks_rows,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_no_host_in_context_returns_true() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware")})
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            [],
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is True
    )


def test_empty_hostname_returns_false() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware")})
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            [("host", "")],
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_integer_hostname_returns_false() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware")})
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            [("host", 1)],
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_invalid_hostname_returns_false() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware")})
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            [("host", "bad/host")],
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_valid_hostname_but_no_site_returns_false() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware")})
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            [("host", "myhost")],
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_valid_hostname_but_empty_site_returns_false() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware")})
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            [("host", "myhost"), ("site", "")],
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is False
    )


def test_returns_true_when_path_exists_in_tree() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware", "cpu")})
    context_vars: HTTPVariables = [("host", "myhost"), ("site", "mysite")]
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            context_vars,
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is True
    )


def test_returns_false_when_path_missing_in_tree() -> None:
    visual = _make_visual({"has_inventory_tree": _path("hardware", "cpu")})
    context_vars: HTTPVariables = [("host", "myhost"), ("site", "mysite")]
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            context_vars,
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_not_found,
        )
        is False
    )


def test_history_returns_true_when_path_exists() -> None:
    visual = _make_visual({"has_inventory_tree_history": _path("hardware")})
    context_vars: HTTPVariables = [("host", "myhost"), ("site", "mysite")]
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            context_vars,
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_found,
        )
        is True
    )


def test_history_returns_false_when_path_missing() -> None:
    visual = _make_visual({"has_inventory_tree_history": _path("hardware")})
    context_vars: HTTPVariables = [("host", "myhost"), ("site", "mysite")]
    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            context_vars,
            base_link_from=_base_returns_true,
            has_inventory_tree=_tree_not_found,
        )
        is False
    )


def test_returns_true_when_either_tree_or_history_matches() -> None:
    visual = _make_visual(
        {
            "has_inventory_tree": _path("hardware", "cpu"),
            "has_inventory_tree_history": _path("hardware"),
        }
    )
    context_vars: HTTPVariables = [("host", "myhost"), ("site", "mysite")]

    def only_history(
        hostname: HostName, site_id: SiteId, path: SDPath | None, is_history: bool
    ) -> bool:
        return is_history and path is not None

    assert (
        _compute_link_from_result(
            [],
            [],
            visual,
            context_vars,
            base_link_from=_base_returns_true,
            has_inventory_tree=only_history,
        )
        is True
    )
