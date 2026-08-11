#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterator

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.search.quicksearch import ABCQuicksearchConductor, IncorrectLabelInputError
from cmk.gui.sidebar._snapin._quicksearch_manager import SnapinQuicksearchManager, TooManyRowsError
from cmk.gui.sidebar._snapin._search import (
    _build_quicksearch_manager_from_context,
    _maybe_strip,
    _render_quicksearch_results,
    QuicksearchSnapin,
)
from cmk.gui.type_defs import SearchResult
from cmk.gui.utils.output_funnel import output_funnel


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request)


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="none_stays_none"),
        pytest.param("", "", id="empty_stays_empty"),
        pytest.param("  heute  ", "heute", id="surrounding_whitespace_is_dropped"),
        pytest.param("   ", "", id="whitespace_only_becomes_empty"),
    ],
)
def test_maybe_strip(value: str | None, expected: str | None) -> None:
    assert _maybe_strip(value) == expected


def test_snapin_metadata() -> None:
    assert QuicksearchSnapin.type_name() == "search"
    assert QuicksearchSnapin.title() == "Quick search"
    assert "h:" in QuicksearchSnapin.description()


def test_page_handlers_expose_both_search_endpoints() -> None:
    assert sorted(QuicksearchSnapin().page_handlers()) == ["ajax_search", "search_open"]


@pytest.mark.usefixtures("patch_theme")
def test_show_renders_and_registers_the_search_field(load_config: Config) -> None:
    with output_funnel.plugged():
        QuicksearchSnapin().show(load_config)
        rendered = output_funnel.drain()

    assert 'id="mk_side_search_field"' in rendered
    assert "cmk.quicksearch.register_search_field('mk_side_search_field');" in rendered
    assert "cmk.quicksearch.on_search_click();" in rendered


def test_build_quicksearch_manager_takes_the_limits_from_the_config(load_config: Config) -> None:
    config = dataclasses.replace(
        load_config, quicksearch_dropdown_limit=42, quicksearch_search_order=[("h", "continue")]
    )

    manager = _build_quicksearch_manager_from_context(_page_context(config))

    assert manager._row_limit == 42
    assert list(manager._search_order) == [("h", "continue")]


def test_render_results_hides_the_topic_for_a_single_match_group() -> None:
    """With only one group the topic heading is pure noise in the narrow sidebar."""
    with output_funnel.plugged():
        _render_quicksearch_results(
            iter([("Hosts", [SearchResult(title="heute", url="view.py")])]), "heute"
        )
        rendered = output_funnel.drain()

    assert 'class="topic"' not in rendered
    assert "heute" in rendered


def test_render_results_shows_the_topics_of_several_match_groups() -> None:
    with output_funnel.plugged():
        _render_quicksearch_results(
            iter(
                [
                    ("Services", [SearchResult(title="CPU", url="view.py")]),
                    ("Hosts", [SearchResult(title="heute", url="view.py")]),
                ]
            ),
            "heute",
        )
        rendered = output_funnel.drain()

    assert rendered.count('class="topic"') == 2
    assert rendered.index("Hosts") < rendered.index("Services")


def test_render_results_sorts_the_matches_of_a_group_by_title() -> None:
    with output_funnel.plugged():
        _render_quicksearch_results(
            iter(
                [
                    (
                        "Hosts",
                        [
                            SearchResult(title="zeta", url="view.py"),
                            SearchResult(title="alpha", url="view.py"),
                        ],
                    )
                ]
            ),
            "a",
        )
        rendered = output_funnel.drain()

    assert rendered.index("alpha") < rendered.index("zeta")


def test_render_results_appends_the_context_of_a_match() -> None:
    with output_funnel.plugged():
        _render_quicksearch_results(
            iter([("Services", [SearchResult(title="CPU", url="view.py", context="on heute")])]),
            "CPU",
        )
        rendered = output_funnel.drain()

    assert "CPU" in rendered
    assert "on heute" in rendered
    assert "<b>" in rendered


def test_ajax_search_ignores_a_blank_query(load_config: Config) -> None:
    request.set_var("q", "   ")

    with output_funnel.plugged():
        QuicksearchSnapin()._ajax_search(_page_context(load_config))
        assert output_funnel.drain() == ""


def test_ajax_search_ignores_a_missing_query(load_config: Config) -> None:
    with output_funnel.plugged():
        QuicksearchSnapin()._ajax_search(_page_context(load_config))
        assert output_funnel.drain() == ""


def _ajax_search(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
    *,
    raised: Exception | None = None,
    search_objects: list[ABCQuicksearchConductor] | None = None,
) -> str:
    request.set_var("q", "heute")
    with monkeypatch.context() as m:
        m.setattr(
            SnapinQuicksearchManager,
            "determine_search_objects",
            lambda self, query, permissions: search_objects if search_objects is not None else [],
        )

        def _conduct(self: SnapinQuicksearchManager, objects: object) -> None:
            if raised is not None:
                raise raised

        m.setattr(SnapinQuicksearchManager, "conduct_search", _conduct)
        m.setattr(
            SnapinQuicksearchManager,
            "evaluate_results",
            lambda self, objects: iter([("Hosts", [SearchResult(title="heute", url="view.py")])]),
        )
        with output_funnel.plugged():
            QuicksearchSnapin()._ajax_search(_page_context(config))
            return output_funnel.drain()


def test_ajax_search_renders_nothing_when_no_plugin_answered(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """Without a single search object there is nothing to evaluate; the dropdown stays
    empty instead of rendering an empty result frame."""
    assert _ajax_search(monkeypatch, load_config, search_objects=[]) == ""


def test_ajax_search_renders_the_results(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    conductors: list[ABCQuicksearchConductor] = [None]  # type: ignore[list-item]

    assert "heute" in _ajax_search(monkeypatch, load_config, search_objects=conductors)


def test_ajax_search_warns_when_the_result_set_is_truncated(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The rows collected before the limit was hit are still worth showing, so the limit is
    a warning next to the results rather than an error replacing them."""
    conductors: list[ABCQuicksearchConductor] = [None]  # type: ignore[list-item]
    rendered = _ajax_search(
        monkeypatch,
        load_config,
        raised=TooManyRowsError("More than 10 results"),
        search_objects=conductors,
    )

    assert "More than 10 results" in rendered
    assert "heute" in rendered


def test_ajax_search_swallows_an_invalid_label_input(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """A half-typed label filter is the normal state while typing - it must not flash an
    error into the dropdown."""
    conductors: list[ABCQuicksearchConductor] = [None]  # type: ignore[list-item]
    rendered = _ajax_search(
        monkeypatch,
        load_config,
        raised=IncorrectLabelInputError("hl", "not a label"),
        search_objects=conductors,
    )

    assert "not a label" not in rendered


def test_ajax_search_reports_a_checkmk_exception(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    conductors: list[ABCQuicksearchConductor] = [None]  # type: ignore[list-item]
    rendered = _ajax_search(
        monkeypatch,
        load_config,
        raised=MKGeneralException("Livestatus is gone"),
        search_objects=conductors,
    )

    assert "Livestatus is gone" in rendered


def test_ajax_search_reports_an_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    conductors: list[ABCQuicksearchConductor] = [None]  # type: ignore[list-item]
    rendered = _ajax_search(
        monkeypatch, load_config, raised=ValueError("boom"), search_objects=conductors
    )

    assert "boom" in rendered
    assert "Traceback" in rendered


def test_ajax_search_reraises_an_unexpected_exception_in_debug_mode(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    conductors: list[ABCQuicksearchConductor] = [None]  # type: ignore[list-item]
    with pytest.raises(ValueError, match="boom"):
        _ajax_search(
            monkeypatch,
            dataclasses.replace(load_config, debug=True),
            raised=ValueError("boom"),
            search_objects=conductors,
        )


def test_search_open_ignores_a_blank_query(load_config: Config) -> None:
    """No query means no redirect - the user stays where they are."""
    request.set_var("q", "  ")

    QuicksearchSnapin()._page_search_open(_page_context(load_config))


def test_search_open_redirects_to_the_generated_view(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("q", "heute")
    with monkeypatch.context() as m:
        m.setattr(
            SnapinQuicksearchManager,
            "generate_search_url",
            lambda self, query, permissions: "view.py?view_name=allhosts",
        )
        with pytest.raises(HTTPRedirect) as redirect:
            QuicksearchSnapin()._page_search_open(_page_context(load_config))

    assert redirect.value.url == "view.py?view_name=allhosts"
