#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved."""

# See https://github.com/pylint-dev/pylint/issues/3488
from __future__ import annotations

import dataclasses
import enum
import json
import logging
import time
import traceback
from collections.abc import Iterable, Iterator, Mapping, Sequence
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any, assert_never, Literal, Self, TypedDict

from livestatus import LocalConnection, SiteConfigurations

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site, SiteId

from cmk.utils.statename import short_service_state_name

import cmk.gui.sites
from cmk.gui import log
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.utils import escaping
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    LocalAutomationConfig,
    make_automation_config,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.sites import get_effective_global_setting


class ACResultState(enum.IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2

    @property
    def short_name(self) -> str:
        return short_service_state_name(self.value)

    @classmethod
    def worst(cls, states: Iterable[Self]) -> Self:
        return max(states)


@dataclasses.dataclass(frozen=True)
class ACSingleResult:
    state: ACResultState
    text: str
    site_id: SiteId
    path: Path | None = None


@dataclasses.dataclass(frozen=True)
class ACTestResult:
    state: ACResultState
    text: str
    test_id: str
    category: str
    title: str
    help: str
    site_id: SiteId
    path: Path | None

    @property
    def state_marked_text(self) -> str:
        match self.state:
            case ACResultState.OK:
                return self.text
            case ACResultState.WARN:
                return f"{self.text} (!)"
            case ACResultState.CRIT:
                return f"{self.text} (!!)"
        assert_never(self.state)

    @classmethod
    def from_repr(cls, repr_data: Mapping[str, Any]) -> Self:
        return cls(
            state=ACResultState(repr_data["state"]),
            text=repr_data["text"],
            site_id=SiteId(repr_data["site_id"]),
            test_id=repr_data["test_id"],
            category=repr_data["category"],
            title=repr_data["title"],
            help=repr_data["help"],
            path=None if (p := repr_data.get("path")) is None else Path(p),
        )

    def __repr__(self) -> str:
        return repr(
            {
                "site_id": self.site_id,
                "state": self.state.value,
                "text": self.text,
                # These fields are be static - at least for the current version, but
                # we transfer them to the central system to be able to handle test
                # results of tests not known to the central site.
                "test_id": self.test_id,
                "category": self.category,
                "title": self.title,
                "help": self.help,
                # this field is needed by 2.2 central sites to deserialize
                "class_name": {
                    ACResultState.OK: "ACResultOK",
                    ACResultState.WARN: "ACResultWARN",
                    ACResultState.CRIT: "ACResultCRIT",
                }[self.state],
                "path": str(self.path) if self.path else None,
            }
        )


class ACTestCategories:
    connectivity = "connectivity"
    usability = "usability"
    performance = "performance"
    security = "security"
    reliability = "reliability"
    deprecations = "deprecations"

    @classmethod
    def title(cls, ident):
        return {
            "connectivity": _("Connectivity"),
            "usability": _("Usability"),
            "performance": _("Performance"),
            "security": _("Security"),
            "reliability": _("Reliability"),
            "deprecations": _("Deprecations"),
        }[ident]


class ACTest:
    def id(self) -> str:
        return self.__class__.__name__

    def category(self) -> str:
        """Return the internal name of the category the BP test is associated with"""
        raise NotImplementedError()

    def title(self) -> str:
        raise NotImplementedError()

    def help(self) -> str:
        raise NotImplementedError()

    def is_relevant(self) -> bool:
        """A test can check whether or not is relevant for the current evnironment.
        In case this method returns False, the check will not be executed and not
        be shown to the user."""
        raise NotImplementedError()

    def execute(self) -> Iterator[ACSingleResult]:
        """Implement the test logic here. The method needs to add one or more test
        results like this:

        yield ACResultOK(_("it's fine"))
        """
        raise NotImplementedError()

    def run(self) -> Iterator[ACTestResult]:
        try:
            for result in self.execute():
                yield ACTestResult(
                    state=result.state,
                    text=result.text,
                    site_id=result.site_id,
                    test_id=self.id(),
                    category=self.category(),
                    title=self.title(),
                    help=self.help(),
                    path=result.path,
                )
        except Exception:
            gui_logger.exception("error executing configuration test %s", self.__class__.__name__)
            yield ACTestResult(
                state=ACResultState.CRIT,
                text="<pre>%s</pre>"
                % _("Failed to execute the test %s: %s")
                % (escaping.escape_attribute(self.__class__.__name__), traceback.format_exc()),
                test_id=self.id(),
                category=self.category(),
                title=self.title(),
                help=self.help(),
                site_id=omd_site(),
                path=None,
            )

    def _uses_microcore(self) -> bool:
        """Whether or not the local site is using the CMC"""
        local_connection = LocalConnection()
        version = local_connection.query_value("GET status\nColumns: program_version\n", deflt="")
        return version.startswith("Check_MK")

    def _get_effective_global_setting(self, varname: str) -> Any:
        return get_effective_global_setting(
            omd_site(),
            is_wato_slave_site(),
            varname,
        )


class ACTestRegistry(cmk.ccc.plugin_registry.Registry[type[ACTest]]):
    def plugin_name(self, instance: type[ACTest]) -> str:
        return instance.__name__


ac_test_registry = ACTestRegistry()


class _TCheckAnalyzeConfig(TypedDict):
    categories: Sequence[str] | None


class AutomationCheckAnalyzeConfig(AutomationCommand[_TCheckAnalyzeConfig]):
    def command_name(self) -> str:
        return "check-analyze-config"

    def get_request(self) -> _TCheckAnalyzeConfig:
        raw_categories = request.get_request().get("categories")
        return _TCheckAnalyzeConfig(
            categories=json.loads(raw_categories) if raw_categories else None
        )

    def execute(self, api_request: _TCheckAnalyzeConfig) -> list[ACTestResult]:
        categories = api_request["categories"]
        results: list[ACTestResult] = []
        for test_cls in ac_test_registry.values():
            test = test_cls()

            if categories and test.category() not in categories:
                continue

            if not test.is_relevant():
                continue

            for result in test.run():
                results.append(result)

        return results


class _TestResult(TypedDict):
    state: Literal[0, 1]
    ac_test_results: Sequence[ACTestResult]
    error: str


def _perform_tests_for_site(
    logger: logging.Logger,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    request_: Request,
    site_id: SiteId,
    categories: Sequence[str] | None,
    debug: bool,
) -> _TestResult:
    # Executes the tests on the site. This method is executed in a dedicated
    # thread (One per site)
    logger.debug("[%s] Starting" % site_id)
    try:
        if isinstance(automation_config, LocalAutomationConfig):
            automation = AutomationCheckAnalyzeConfig()
            ac_test_results = automation.execute(_TCheckAnalyzeConfig(categories=categories))
        else:
            raw_ac_test_results = do_remote_automation(
                automation_config,
                "check-analyze-config",
                [("categories", json.dumps(categories))],
                timeout=request_.request_timeout - 10,
                debug=debug,
            )
            assert isinstance(raw_ac_test_results, list)
            ac_test_results = [ACTestResult.from_repr(r) for r in raw_ac_test_results]

        logger.debug("[%s] Finished: %r", site_id, ac_test_results)
        return _TestResult(
            state=0,
            ac_test_results=ac_test_results,
            error="",
        )

    except Exception:
        logger.exception("[%s] Failed" % site_id)
        return _TestResult(
            state=1,
            ac_test_results=[],
            error="Traceback:<br>%s" % (traceback.format_exc().replace("\n", "<br>\n")),
        )


def _connectivity_result(*, state: ACResultState, text: str, site_id: SiteId) -> ACTestResult:
    return ACTestResult(
        state=state,
        text=text,
        site_id=site_id,
        test_id="ACTestConnectivity",
        category=ACTestCategories.connectivity,
        title=_("Site connectivity"),
        help=_("This check returns CRIT if the connection to the remote site failed."),
        path=None,
    )


def _error_callback(error: BaseException) -> None:
    # for exceptions that could not be handled within the function, e.g. calling with incorrect
    # number of arguments
    log.logger.error(str(error))


def perform_tests(
    logger: logging.Logger,
    request_: Request,
    test_sites: SiteConfigurations,
    *,
    categories: Sequence[str] | None,  # 'None' means 'No filtering'
    debug: bool,
) -> Mapping[SiteId, Sequence[ACTestResult]]:
    logger.debug("Executing tests for %d sites" % len(test_sites))
    if not test_sites:
        return {}

    pool = ThreadPool(processes=len(test_sites))

    def run(site_id: SiteId) -> _TestResult:
        return _perform_tests_for_site(
            logger,
            make_automation_config(test_sites[site_id]),
            request_,
            site_id,
            categories,
            debug,
        )

    active_tasks = {
        site_id: pool.apply_async(
            func=copy_request_context(run),
            args=(site_id,),
            error_callback=_error_callback,
        )
        for site_id in test_sites
    }

    results_by_site_id: dict[SiteId, list[ACTestResult]] = {}
    while active_tasks:
        time.sleep(0.1)
        for site_id, async_result in list(active_tasks.items()):
            try:
                if not async_result.ready():
                    continue

                active_tasks.pop(site_id)
                result = async_result.get()

                if result["state"] == 1:
                    raise MKGeneralException(result["error"])

                if result["state"] == 0:
                    ac_test_results = result["ac_test_results"]
                    if categories and "connectivity" in categories:
                        # Add general connectivity result
                        ac_test_results.append(
                            _connectivity_result(
                                state=ACResultState.OK,
                                text=_("No connectivity problems"),
                                site_id=site_id,
                            )
                        )
                    results_by_site_id[site_id] = ac_test_results

                else:
                    raise NotImplementedError()

            except Exception as e:
                if categories and "connectivity" in categories:
                    results_by_site_id[site_id] = [
                        _connectivity_result(
                            state=ACResultState.CRIT,
                            text=str(e),
                            site_id=site_id,
                        )
                    ]
                logger.exception("error analyzing configuration for site %s", site_id)

    logger.debug("Got test results")
    return results_by_site_id


def _merge_test_results_of_site(
    site_id: SiteId,
    test_results_of_site: Sequence[ACTestResult],
) -> Iterator[ACTestResult]:
    test_results_by_test_id: dict[str, list[ACTestResult]] = {}
    for test_result in test_results_of_site:
        test_results_by_test_id.setdefault(test_result.test_id, []).append(test_result)

    for test_id, test_results in test_results_by_test_id.items():
        # Do not merge test_results that have been gathered on one site for different sites
        num_sites = len({r.site_id for r in test_results})
        if num_sites > 1:
            yield from test_results
        elif test_results:
            first = test_results[0]
            yield ACTestResult(
                state=ACResultState.worst(r.state for r in test_results),
                text=", ".join(r.state_marked_text for r in test_results),
                test_id=test_id,
                category=first.category,
                title=first.title,
                help=first.help,
                site_id=site_id,
                path=None,
            )


def merge_tests(
    test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
) -> Mapping[SiteId, Sequence[ACTestResult]]:
    return {
        site_id: merged
        for site_id, test_results_of_site in test_results_by_site_id.items()
        if (merged := list(_merge_test_results_of_site(site_id, test_results_of_site)))
    }
