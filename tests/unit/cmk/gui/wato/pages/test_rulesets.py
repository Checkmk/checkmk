#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from cmk.utils.rulesets.conditions import HostOrServiceConditions
from cmk.utils.rulesets.ruleset_matcher import TagConditionNE
from cmk.utils.tags import TagConfig, TagGroupID, TagID

from cmk.gui.config import active_config
from cmk.gui.utils.html import HTML
from cmk.gui.wato.pages.rulesets import RuleConditionRenderer
from cmk.gui.watolib.hosts_and_folders import FolderLookupCache, Host


@pytest.fixture(name="tag_config")
def fixture_tag_config():
    tag_config = TagConfig.from_config(
        {
            "aux_tags": [
                {
                    "id": TagID("aux_tag_1"),
                    "topic": "Auxiliary tags",
                    "title": "Auxiliary tag 1",
                }
            ],
            "tag_groups": [
                {
                    "id": TagGroupID("tag_grp_1"),
                    "topic": "Topic 1",
                    "title": "Tag group 1",
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": TagID("grp_1_tg_1"),
                            "title": "Tag 1.1",
                        },
                        {
                            "aux_tags": [],
                            "id": TagID("grp_1_tg_2"),
                            "title": "Tag 1.2",
                        },
                    ],
                },
                {
                    "id": TagGroupID("tag_grp_2"),
                    "topic": "Topic 2",
                    "title": "Tag group 2",
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": TagID("grp_2_tg_1"),
                            "title": "Tag 2.1",
                        },
                        {
                            "aux_tags": [],
                            "id": TagID("grp_2_tg_2"),
                            "title": "Tag 2.2",
                        },
                    ],
                },
                {
                    "id": TagGroupID("tag_grp_3"),
                    "topic": "Topic 3",
                    "title": "Tag group 3",
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": TagID("grp_3_tg_1"),
                            "title": "Tag 3.1",
                        },
                    ],
                },
            ],
        }
    )
    return tag_config


@pytest.fixture(autouse=True)
def patch_tag_config(
    request_context: None, monkeypatch: MonkeyPatch, tag_config: TagConfig
) -> Iterable[None]:
    with monkeypatch.context() as m:
        m.setattr(active_config, "tags", tag_config)
        yield


@pytest.fixture(name="folder_lookup")
def fixture_folder_lookup(mocker: MockerFixture) -> None:
    folder_cache = {"cached_host": "cached_host_value"}
    mocker.patch.object(FolderLookupCache, "get_cache", return_value=folder_cache)

    class MockHost:
        def edit_url(self):
            return "cached_host_url"

    mocker.patch.object(Host, "host", return_value=MockHost())


class TestRuleConditionRenderer:
    @pytest.mark.parametrize(
        "taggroup_id, tag_spec, rendered_condition",
        [
            pytest.param(
                "tag_grp_1",
                "grp_1_tg_1",
                HTML.without_escaping("Host tag: Tag group 1 is <b>Tag 1.1</b>"),
                id="grouped tag",
            ),
            pytest.param(
                "tag_grp_1",
                {"$ne": "grp_1_tg_1"},
                HTML.without_escaping("Host tag: Tag group 1 is <b>not</b> <b>Tag 1.1</b>"),
                id="negated grouped tag",
            ),
            pytest.param(
                "aux_tag_1",
                "aux_tag_1",
                HTML.without_escaping("Host has tag <b>Auxiliary tag 1</b>"),
                id="auxiliary tag",
            ),
            pytest.param(
                "aux_tag_1",
                {"$ne": "aux_tag_1"},
                HTML.without_escaping("Host does not have tag <b>Auxiliary tag 1</b>"),
                id="negated auxiliary tag",
            ),
            pytest.param(
                "xyz",
                "a",
                HTML.without_escaping("Unknown tag: Host has the tag <tt>a</tt>"),
                id="unknown tag group",
            ),
            pytest.param(
                "xyz",
                "grp_1_tg_1",
                HTML.without_escaping("Unknown tag: Host has the tag <tt>grp_1_tg_1</tt>"),
                id="unknown tag",
            ),
        ],
    )
    def test_single_tag_condition(
        self,
        taggroup_id: TagGroupID,
        tag_spec: TagID | None | TagConditionNE,
        rendered_condition: HTML,
    ) -> None:
        assert (
            RuleConditionRenderer()._single_tag_condition(
                taggroup_id,
                tag_spec,
            )
            == rendered_condition
        )

    def test_tag_condition(self) -> None:
        assert list(
            RuleConditionRenderer()._tag_conditions(
                {
                    TagGroupID("tag_grp_1"): {
                        "$or": [
                            TagID("grp_1_tg_1"),
                            TagID("grp_1_tg_2"),
                        ]
                    },
                    TagGroupID("tag_grp_2"): {
                        "$nor": [
                            TagID("grp_2_tg_1"),
                            TagID("grp_2_tg_2"),
                        ]
                    },
                    TagGroupID("tag_grp_3"): TagID("grp_3_tg_1"),
                    TagGroupID("aux_tag_1"): {"$ne": TagID("aux_tag_1")},
                }
            )
        ) == [
            HTML.without_escaping(
                "Host tag: Tag group 1 is <b>Tag 1.1</b> <i>or</i> Host tag: Tag group 1 is <b>Tag 1.2</b>"
            ),
            HTML.without_escaping(
                "Neither Host tag: Tag group 2 is <b>Tag 2.1</b> <i>nor</i> Host tag: Tag group 2 is <b>Tag 2.2</b>"
            ),
            HTML.without_escaping("Host tag: Tag group 3 is <b>Tag 3.1</b>"),
            HTML.without_escaping("Host does not have tag <b>Auxiliary tag 1</b>"),
        ]

    # FIXME: add special case if only one regex is given
    @pytest.mark.parametrize(
        "conditions, expected",
        [
            pytest.param(
                [],
                "This rule does <b>never</b> apply due to an empty list of explicit hosts!",
                id="No conditions",
            ),
            pytest.param(
                ["foo"],
                "Host name is <b>foo</b>",
                id="Single host",
            ),
            pytest.param(
                ["foo", "bar"],
                "Host name is <b>foo</b> or <b>bar</b>",
                id="Two hosts names",
            ),
            pytest.param(
                ["foo", "bar", "baz"],
                "Host name is <b>foo</b>, <b>bar</b> or <b>baz</b>",
                id="Three host names",
            ),
            pytest.param(
                [{"$regex": "f?o"}],
                "Host name matches one of regex <b>f?o</b>",
                id="Single regex",
            ),
            pytest.param(
                [{"$regex": "f?o"}, {"$regex": "b.*r"}],
                "Host name matches one of regex <b>f?o</b> or <b>b.*r</b>",
                id="Two regexes",
            ),
            pytest.param(
                [{"$regex": "f?o"}, "bar"],
                "Host name matches regex <b>f?o</b> or is <b>bar</b>",
                id="Regex and host name",
            ),
            pytest.param(
                [{"$regex": "f?o"}, "bar", {"$regex": "ba.*r"}],
                "Host name matches regex <b>f?o</b>, is <b>bar</b> or matches regex <b>ba.*r</b>",
                id="Regex, host name and regex",
            ),
            pytest.param(
                {"$nor": ["foo"]},
                "Host name is not one of <b>foo</b>",
                id="Negation with single host name",
            ),
            pytest.param(
                {"$nor": ["foo", "bar"]},
                "Host name is not one of <b>foo</b> or <b>bar</b>",
                id="Negation with two host names",
            ),
            pytest.param(
                {"$nor": [{"$regex": "f?o"}]},
                "Host name is not one of regex <b>f?o</b>",
                id="Negation with one regex",
            ),
            pytest.param(
                {"$nor": [{"$regex": "f?o"}, {"$regex": "b.*r"}]},
                "Host name is not one of regex <b>f?o</b> or <b>b.*r</b>",
                id="Negation with two regexes",
            ),
            pytest.param(
                {"$nor": [{"$regex": "f?o"}, "bar", {"$regex": "b.*r"}, "foo"]},
                "Host name does not match regex <b>f?o</b>, is not <b>bar</b>, does not match regex <b>b.*r</b> or is not <b>foo</b>",
                id="Negation with regex, host name and regex",
            ),
            pytest.param(
                ["cached_host"],
                'Host name is <b><a href="cached_host_url">cached_host</a></b>',
                id="Host with folder hint",
            ),
            pytest.param(
                [{"$regex": "f?o"}, "cached_host"],
                'Host name matches regex <b>f?o</b> or is <b><a href="cached_host_url">cached_host</a></b>',
                id="Regex and host with folder hint",
            ),
        ],
    )
    @pytest.mark.usefixtures("folder_lookup")
    def test_render_host_condition_text(
        self, conditions: HostOrServiceConditions, expected: str
    ) -> None:
        assert RuleConditionRenderer()._render_host_condition_text(
            conditions
        ) == HTML.without_escaping(expected)

    @pytest.mark.parametrize(
        "conditions, exception",
        [
            pytest.param(
                {"$nor": []},
                IndexError,
                id="FIXME: Negation expects at least one condition",
            ),
            pytest.param(
                {"$nor": [{"foo": "bar"}]},
                ValueError,
                id="Unsupported key in nested dict (mypy should warn)",
            ),
            pytest.param(
                {"foo": []},
                ValueError,
                id="Unsupported key in dict (mypy should warn)",
            ),
        ],
    )
    @pytest.mark.usefixtures("folder_lookup")
    def test_render_host_condition_text_raises(
        self, conditions: HostOrServiceConditions, exception: type[Exception]
    ) -> None:
        with pytest.raises(exception):
            assert RuleConditionRenderer()._render_host_condition_text(conditions)

    @pytest.mark.parametrize(
        "item_type, item_name, conditions, expected",
        [
            pytest.param(
                "foo",
                "bar",
                None,
                [],
                id="conditions is None",
            ),
            pytest.param(
                None,
                "foo",
                [],
                [],
                id="item_type is None",
            ),
            pytest.param(
                "",
                "foo",
                [],
                [],
                id="item_type is empty",
            ),
            pytest.param(
                "service",
                "foo",
                [],
                [HTML.without_escaping("Does not match any service")],
                id="item_type and item_name without conditions",
            ),
            pytest.param(
                "service",
                "foo",
                ["bar"],
                [HTML.without_escaping("Service name is <b>bar</b>")],
                id="item_type and item_name without conditions",
            ),
            pytest.param(
                "item",
                "foo",
                ["bar"],
                [HTML.without_escaping("foo is <b>bar</b>")],
                id="item with one name",
            ),
            pytest.param(
                "item",
                "foo",
                ["bar", "baz"],
                [HTML.without_escaping("foo is <b>bar</b> or <b>baz</b>")],
                id="item with two names",
            ),
            pytest.param(
                "service",
                "foo",
                [{"$regex": "b?r"}, "baz"],
                [
                    HTML.without_escaping(
                        "Service name begins with <b>b?r</b> or begins with <b>baz</b>"
                    )
                ],
                id="service with one regex and one name",
            ),
            pytest.param(
                "service",
                "foo",
                [{"$regex": "b?r"}, {"$regex": "b.*z"}],
                [HTML.without_escaping("Service name begins with <b>b?r</b> or <b>b.*z</b>")],
                id="service with two regexes",
            ),
            pytest.param(
                "item",
                "foo",
                {"$nor": ["bar"]},
                [HTML.without_escaping("foo is not <b>bar</b>")],
                id="negated item with one name",
            ),
            pytest.param(
                "item",
                "foo",
                {"$nor": [{"$regex": "b?z"}]},
                [HTML.without_escaping("foo does not begin with <b>b?z</b>")],
                id="negated item with one regex",
            ),
            pytest.param(
                "item",
                "foo",
                {"$nor": ["bar", "baz"]},
                [HTML.without_escaping("foo is not <b>bar</b> or <b>baz</b>")],
                id="negated item with two names",
            ),
            pytest.param(
                "item",
                "foo",
                {"$nor": ["bar", {"$regex": "b?z"}, "bam"]},
                [
                    HTML.without_escaping(
                        "foo begins not with <b>bar</b>, begins not with <b>b?z</b> or begins not with <b>bam</b>"
                    )
                ],
                id="negated item with two names and one regex",
            ),
            pytest.param(
                "item",
                "foo",
                {"$nor": [{"$regex": "f.*o"}, {"$regex": "b?z"}]},
                [HTML.without_escaping("foo does not begin with <b>f.*o</b> or <b>b?z</b>")],
                id="negated item with two regexes",
            ),
        ],
    )
    def test_service_conditions(
        self,
        item_type: str | None,
        item_name: str | None,
        conditions: HostOrServiceConditions | None,
        expected: list[HTML],
    ) -> None:
        assert (
            list(RuleConditionRenderer()._service_conditions(item_type, item_name, conditions))
            == expected
        )
