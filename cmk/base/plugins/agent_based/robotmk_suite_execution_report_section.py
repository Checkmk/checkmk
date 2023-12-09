#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator, Sequence
from xml.dom.minidom import Element, Node, parseString

import xmltodict

from cmk.plugins.lib.robotmk_rebot_xml import Keyword, KeywordStatus, RFTest, Suite
from cmk.plugins.lib.robotmk_suite_execution_report import (
    RebotOutcomeResult,
    Section,
    SuiteExecutionReport,
    SuiteRebotReport,
    SuiteReport,
    TestReport,
)

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable

_ALLOWED_TAG_NAMES = frozenset(["kw", "test", "for", "if", "branch", "iter"])


def parse(string_table: StringTable) -> Section:
    suites = {}
    tests = {}
    for line in string_table:
        suite_execution_report = SuiteExecutionReport.model_validate_json(line[0])
        (
            suites[suite_execution_report.suite_id],
            tests_of_suite,
        ) = _post_process_suite_execution_report(suite_execution_report)
        tests.update(tests_of_suite)
    return Section(
        suites=suites,
        tests=tests,
    )


def _post_process_suite_execution_report(
    suite_execution_report: SuiteExecutionReport,
) -> tuple[SuiteReport, dict[str, TestReport]]:
    if isinstance(rebot := suite_execution_report.rebot, RebotOutcomeResult):
        return (
            SuiteReport(
                attempts=suite_execution_report.attempts,
                config=suite_execution_report.config,
                rebot=SuiteRebotReport(
                    top_level_suite=rebot.Ok.xml.rebot.robot.suite,
                    timestamp=rebot.Ok.timestamp,
                ),
            ),
            {
                test_name: TestReport(
                    test=test,
                    html=rebot.Ok.html,
                    attempts_config=suite_execution_report.config,
                    rebot_timestamp=rebot.Ok.timestamp,
                )
                for test_name, test in _extract_tests(
                    suite=rebot.Ok.xml.rebot.robot.suite,
                    raw_xml=rebot.Ok.xml.raw_xml,
                    parent_names=[suite_execution_report.suite_id],
                ).items()
            },
        )
    return (
        SuiteReport(
            attempts=suite_execution_report.attempts,
            config=suite_execution_report.config,
            rebot=rebot,
        ),
        {},
    )


def _tests_by_items(
    suite: Suite,
    parent_names: Sequence[str] = (),
) -> dict[str, RFTest]:
    tests_with_full_names = {}

    for test in suite.test:
        test_name = "-".join([*parent_names, suite.name, test.name])
        tests_with_full_names[test_name] = test

    for sub_suite in suite.suite:
        tests_with_full_names |= _tests_by_items(
            sub_suite, parent_names=[*parent_names, suite.name]
        )

    return tests_with_full_names


def _extract_keyword(
    child: Element,
) -> Keyword:
    return Keyword(
        name=child.getAttribute("name"),
        id=child.getAttribute("id"),
        status=KeywordStatus.model_validate(
            xmltodict.parse(child.parentNode.getElementsByTagName("status")[0].toxml())
        ),
    )


def _get_element_nodes(element: Element) -> Iterator[Element]:
    yield from (
        child
        for child in element.childNodes
        if child.nodeType == Node.ELEMENT_NODE and child.tagName in _ALLOWED_TAG_NAMES
    )


def _assign_id_recursive(
    element: Element,
    parent_id: str | None = None,
) -> None:
    for child_index, child in enumerate(_get_element_nodes(element)):
        id_ = f"{parent_id or element.getAttribute('id')}-k{child_index + 1}"

        if child.tagName == "branch":
            _assign_id_recursive(child, element.getAttribute("id"))
            continue

        child.setAttribute("id", id_)
        _assign_id_recursive(child)


def _add_ids_to_elements(elements: list[Element]) -> list[Element]:
    for element in elements:
        _assign_id_recursive(element)
    return elements


def _attach_keywords_to_tests(
    keywords: Iterable[Keyword],
    tests: Iterable[RFTest],
) -> None:
    test_id_to_test = {test.id: test for test in tests}

    for keyword in keywords:
        if (
            keyword.parent_test_id
            and (test := test_id_to_test.get(keyword.parent_test_id)) is not None
        ):
            test.keywords.append(keyword)


def _extract_tests(
    *,
    suite: Suite,
    raw_xml: str,
    parent_names: Sequence[str] = (),
) -> dict[str, RFTest]:
    tests_by_items = _tests_by_items(
        suite,
        parent_names=parent_names,
    )

    keywords = (
        _extract_keyword(kw)
        for element in _add_ids_to_elements(parseString(raw_xml).getElementsByTagName("test"))
        for kw in element.getElementsByTagName("kw")
    )

    _attach_keywords_to_tests(
        keywords,
        tests_by_items.values(),
    )
    return tests_by_items


register.agent_section(
    name="robotmk_suite_execution_report",
    parse_function=parse,
)
