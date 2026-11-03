#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.search.spec import (
    HostAddress,
    HostAlias,
    HostFolder,
    HostGroup,
    HostLabel,
    HostName,
    HostTag,
    parse,
    prefix_of,
    PrefixedSearch,
    SearchParseError,
    ServiceFolder,
    ServiceGroup,
    ServiceLabel,
    ServiceName,
    ServiceState,
    Term,
    UnprefixedSearch,
)


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("h:web", HostName(pattern="web"), id="h"),
        pytest.param("al:Web Server", HostAlias(pattern="Web Server"), id="al"),
        pytest.param("ad:10.0.", HostAddress(pattern="10.0."), id="ad"),
        pytest.param("hg:linux", HostGroup(name="linux"), id="hg"),
        pytest.param("hl:os:linux", HostLabel(key="os", value="linux"), id="hl"),
        pytest.param("tg:criticality:prod", HostTag(group="criticality", tag="prod"), id="tg"),
        pytest.param("hf:linux", HostFolder(path="linux"), id="hf"),
        pytest.param("s:CPU load", ServiceName(pattern="CPU load"), id="s"),
        pytest.param("sg:web", ServiceGroup(name="web"), id="sg"),
        pytest.param("st:crit", ServiceState(state="crit"), id="st"),
        pytest.param("sl:os:linux", ServiceLabel(key="os", value="linux"), id="sl"),
        pytest.param("sf:linux", ServiceFolder(path="linux"), id="sf"),
    ],
)
def test_prefix_becomes_its_term(query: str, expected: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((expected,),))


def test_same_prefix_is_one_or_clause() -> None:
    assert parse("h:web h:db") == PrefixedSearch(
        clauses=((HostName(pattern="web"), HostName(pattern="db")),)
    )


@pytest.mark.parametrize(
    "query, first, second",
    [
        pytest.param("tg:prod tg:linux", HostTag(None, "prod"), HostTag(None, "linux"), id="tg"),
        pytest.param("hl:a:1 hl:b:2", HostLabel("a", "1"), HostLabel("b", "2"), id="hl"),
        pytest.param("sl:a:1 sl:b:2", ServiceLabel("a", "1"), ServiceLabel("b", "2"), id="sl"),
    ],
)
def test_repeated_tags_and_labels_are_and_clauses(query: str, first: Term, second: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((first,), (second,)))


def test_different_prefixes_are_and_clauses_in_order_of_appearance() -> None:
    assert parse("s:cpu h:web ad:10. h:db") == PrefixedSearch(
        clauses=(
            (ServiceName(pattern="cpu"),),
            (HostName(pattern="web"), HostName(pattern="db")),
            (HostAddress(pattern="10."),),
        )
    )


def test_value_runs_up_to_the_next_prefix_and_is_stripped() -> None:
    assert parse("  h:  web server   s:Check_MK Discovery ") == PrefixedSearch(
        clauses=((HostName(pattern="web server"),), (ServiceName(pattern="Check_MK Discovery"),))
    )


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("st:warn|crit", id="pipe"),
        pytest.param("st:(warn|crit)", id="parentheses"),
        pytest.param("st:warn st:crit", id="repeated"),
        pytest.param("st:WARN | Crit", id="case-insensitive"),
    ],
)
def test_several_service_states_are_one_or_clause(query: str) -> None:
    assert parse(query) == PrefixedSearch(
        clauses=((ServiceState(state="warn"), ServiceState(state="crit")),)
    )


def test_tag_without_group_leaves_group_open() -> None:
    assert parse("tg:prod") == PrefixedSearch(clauses=((HostTag(group=None, tag="prod"),),))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hl: os:linux", HostLabel(key="os", value="linux"), id="hl"),
        pytest.param("sl:  os:linux", ServiceLabel(key="os", value="linux"), id="sl"),
        pytest.param("tg: dc:fra", HostTag(group="dc", tag="fra"), id="tg"),
    ],
)
def test_key_after_whitespace_is_no_prefix(query: str, expected: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((expected,),))


def test_prefix_after_label_value_is_a_prefix() -> None:
    assert parse("hl: os:linux h:web") == PrefixedSearch(
        clauses=((HostLabel(key="os", value="linux"),), (HostName(pattern="web"),))
    )


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hl:os : linux", HostLabel(key="os", value="linux"), id="hl"),
        pytest.param("sl:os: linux", ServiceLabel(key="os", value="linux"), id="sl"),
        pytest.param("tg:dc: fra", HostTag(group="dc", tag="fra"), id="tg"),
    ],
)
def test_whitespace_around_inner_colon_is_ignored(query: str, expected: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((expected,),))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hl:os:lin*", HostLabel(key="os", value="lin*"), id="hl"),
        pytest.param("sl:os:lin*", ServiceLabel(key="os", value="lin*"), id="sl"),
        pytest.param("tg:os:lin*", HostTag(group="os", tag="lin*"), id="tg"),
    ],
)
def test_trailing_star_of_label_or_tag_is_kept_as_prefix_match(query: str, expected: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((expected,),))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hl:os:*", HostLabel(key="os", value="*"), id="hl"),
        pytest.param("sl:os: *", ServiceLabel(key="os", value="*"), id="sl"),
        pytest.param("tg:os:*", HostTag(group="os", tag="*"), id="tg"),
    ],
)
def test_star_as_value_or_tag_matches_any_of_the_key_or_group(query: str, expected: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((expected,),))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hl:cmk/aws*", HostLabel(key="cmk/aws*", value=None), id="hl"),
        pytest.param("sl:cmk/aws*", ServiceLabel(key="cmk/aws*", value=None), id="sl"),
    ],
)
def test_label_key_prefix_matches_any_value(query: str, expected: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((expected,),))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hg:linux*", HostGroup(name="linux*"), id="hg-prefix"),
        pytest.param("sg:web*", ServiceGroup(name="web*"), id="sg-prefix"),
        pytest.param("hg:^lin.x", HostGroup(name="^lin.x"), id="no-regex"),
        pytest.param("hg:*linux", HostGroup(name="*linux"), id="leading-star-is-literal"),
    ],
)
def test_group_is_a_name_or_name_prefix(query: str, expected: Term) -> None:
    assert parse(query) == PrefixedSearch(clauses=((expected,),))


def test_label_value_keeps_further_colons() -> None:
    assert parse("hl:os:windows:95") == PrefixedSearch(
        clauses=((HostLabel(key="os", value="windows:95"),),)
    )


@pytest.mark.parametrize(
    "query, pattern",
    [
        pytest.param("h:db*", "db.*", id="glob"),
        pytest.param("h:*web*01", ".*web.*01", id="several-globs"),
        pytest.param("h:web[0-9]*", "web[0-9].*", id="star-after-regex-construct"),
        pytest.param("h:^web-(01|02)$", "^web-(01|02)$", id="regex"),
    ],
)
def test_regex_terms_turn_globs_into_regex(query: str, pattern: str) -> None:
    assert parse(query) == PrefixedSearch(clauses=((HostName(pattern=pattern),),))


@pytest.mark.parametrize(
    "query, path",
    [
        pytest.param("hf:/linux/web/", "linux/web", id="slashes-stripped"),
        pytest.param("hf:lin*/web", "lin*/web", id="glob-kept"),
        pytest.param("hf:a.b", "a.b", id="literal-dot"),
    ],
)
def test_folder_is_a_path_glob(query: str, path: str) -> None:
    assert parse(query) == PrefixedSearch(clauses=((HostFolder(path=path),),))


def test_service_folder_is_a_path_glob() -> None:
    assert parse("sf:/lin*/web/") == PrefixedSearch(clauses=((ServiceFolder(path="lin*/web"),),))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("h:web\nserver", "h:web server", id="in-value"),
        pytest.param("h:web\r\ns:cpu", "h:web s:cpu", id="between-terms"),
        pytest.param("web\r\nserver", "web server", id="without-prefix"),
        pytest.param("h:web\tserver", "h:web server", id="tab"),
        pytest.param("h:web\u2028server", "h:web server", id="unicode-line-separator"),
    ],
)
def test_line_break_or_control_character_counts_as_space(query: str, expected: str) -> None:
    assert parse(query) == parse(expected)


def test_query_without_prefix_is_one_pattern() -> None:
    assert parse("  web*  ") == UnprefixedSearch(text="web*", pattern="web.*")


def test_query_without_prefix_keeps_inner_whitespace() -> None:
    assert parse("web server") == UnprefixedSearch(text="web server", pattern="web server")


@pytest.mark.parametrize(
    "query, message",
    [
        pytest.param("h:web(", "not a valid regular expression", id="unbalanced"),
        pytest.param("s:[a-", "not a valid regular expression", id="unterminated-set"),
        pytest.param("web(", "not a valid regular expression", id="without-prefix"),
        pytest.param("h:(?!web)", "look-around", id="lookahead"),
        pytest.param("h:(?<=a)b", "look-around", id="lookbehind"),
    ],
)
def test_invalid_regex_is_rejected(query: str, message: str) -> None:
    with pytest.raises(SearchParseError, match=message):
        parse(query)


@pytest.mark.parametrize(
    "query, message",
    [
        pytest.param("", "enter a search term", id="empty"),
        pytest.param("   ", "enter a search term", id="blank"),
        pytest.param("x:web", "Unknown search prefix", id="unknown-prefix"),
        pytest.param("hh:web", "Unknown search prefix", id="unknown-two-letter-prefix"),
        pytest.param("h:web sx:cpu", "Unknown search prefix", id="unknown-prefix-after-known"),
        pytest.param("al:rack a: 4", "Unknown search prefix", id="prefix-shaped-word-in-value"),
        pytest.param("tg:dc : ", "not a host tag", id="tag-of-only-whitespace"),
        pytest.param("h:", "needs a value", id="prefix-without-value"),
        pytest.param("h: s:cpu", "needs a value", id="prefix-without-value-before-next"),
        pytest.param("hl: ", "needs a value", id="key-value-prefix-without-value"),
        pytest.param("web h:db", "not preceded by a search prefix", id="text-before-first-prefix"),
        pytest.param("hl:linux", "not a label", id="label-without-colon"),
        pytest.param("sl::linux", "not a label", id="label-without-key"),
        pytest.param("hl:os:", "not a label", id="label-without-value"),
        pytest.param("tg::prod", "not a host tag", id="tag-without-group"),
        pytest.param("tg:group:", "not a host tag", id="tag-without-tag"),
        pytest.param("hl:*", 'e.g. "cmk/aws\\*"', id="label-key-only-star"),
        pytest.param("hl:*:linux", "cannot stand for any", id="label-key-star-with-value"),
        pytest.param("tg:*:prod", "cannot stand for any", id="tag-group-star"),
        pytest.param("tg:*", "needs text before it", id="tag-without-group-only-star"),
        pytest.param("hg:*", "needs text before it", id="host-group-only-star"),
        pytest.param("sg:*", "needs text before it", id="service-group-only-star"),
        pytest.param("st:broken", "Unknown service state", id="unknown-state"),
        pytest.param("st:warn|", "empty service state", id="empty-state"),
        pytest.param("st:warn||crit", "empty service state", id="empty-state-between"),
        pytest.param("st:()", "empty service state", id="empty-parentheses"),
        pytest.param("st:(warn|crit", "Unknown service state", id="unbalanced-open"),
        pytest.param("st:warn|crit)", "Unknown service state", id="unbalanced-close"),
        pytest.param("hf:/", "not a folder path", id="empty-folder"),
    ],
)
def test_invalid_query_is_rejected(query: str, message: str) -> None:
    with pytest.raises(SearchParseError, match=message):
        parse(query)


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("C:drive", id="capitalised"),
        pytest.param("note: rack 4", id="longer-word"),
        pytest.param("dead::1", id="ipv6"),
    ],
)
def test_word_with_colon_that_is_not_prefix_shaped_is_text(query: str) -> None:
    assert parse(query) == UnprefixedSearch(text=query, pattern=query)


def test_word_with_colon_that_is_not_prefix_shaped_is_part_of_the_value() -> None:
    assert parse("al:web note: rack 4") == PrefixedSearch(
        clauses=((HostAlias(pattern="web note: rack 4"),),)
    )


@pytest.mark.parametrize(
    "query",
    [
        pytest.param(query, id=query.split(":")[0])
        for query in (
            "h:web",
            "al:web",
            "ad:10.0.0.1",
            "hg:linux",
            "hl:os:linux",
            "tg:prod",
            "hf:linux",
            "s:cpu",
            "sg:web",
            "st:warn",
            "sl:os:linux",
            "sf:linux",
        )
    ],
)
def test_prefix_of_a_term_is_the_prefix_it_was_given_with(query: str) -> None:
    spec = parse(query)
    assert isinstance(spec, PrefixedSearch)

    assert [prefix_of(term) for clause in spec.clauses for term in clause] == [
        query.split(":", maxsplit=1)[0]
    ]
