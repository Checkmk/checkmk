#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved."""

# See https://github.com/pylint-dev/pylint/issues/3488
from __future__ import annotations

import ast
import dataclasses
import enum
import json
import logging
import multiprocessing
import queue
import time
import traceback
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, assert_never, Self, TypedDict

from livestatus import LocalConnection, SiteConfigurations, SiteId

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site

from cmk.utils.statename import short_service_state_name

import cmk.gui.sites
from cmk.gui import log
from cmk.gui.config import Config
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.site_config import get_site_config, is_wato_slave_site, site_is_local
from cmk.gui.utils import escaping
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation
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


@dataclasses.dataclass(frozen=True)
class ACTestResult:
    state: ACResultState
    text: str
    test_id: str
    category: str
    title: str
    help: str
    site_id: SiteId

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
            # Do not merge results that have been gathered on one site for different sites
            results = list(self.execute())
            num_sites = len({r.site_id for r in results})
            if num_sites > 1:
                yield from (
                    ACTestResult(
                        state=result.state,
                        text=result.text,
                        site_id=result.site_id,
                        test_id=self.id(),
                        category=self.category(),
                        title=self.title(),
                        help=self.help(),
                    )
                    for result in results
                )
                return

            yield ACTestResult(
                state=(
                    ACResultState.worst(r.state for r in results) if results else ACResultState.OK
                ),
                text=", ".join(r.state_marked_text for r in results),
                test_id=self.id(),
                category=self.category(),
                title=self.title(),
                help=self.help(),
                site_id=omd_site(),
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


def _perform_tests_for_site(
    logger: logging.Logger,
    active_config: Config,
    request_: Request,
    site_id: SiteId,
    categories: Sequence[str] | None,
    result_queue: multiprocessing.JoinableQueue[tuple[SiteId, str]],
) -> None:
    # Executes the tests on the site. This method is executed in a dedicated
    # subprocess (One per site)
    logger.debug("[%s] Starting" % site_id)
    result = None
    try:
        # Would be better to clean all open fds that are not needed, but we don't
        # know the FDs of the result_queue pipe. Can we find it out somehow?
        # Cleanup resources of the apache
        # for x in range(3, 256):
        #    try:
        #        os.close(x)
        #    except OSError, e:
        #        if e.errno == errno.EBADF:
        #            pass
        #        else:
        #            raise

        # Reinitialize logging targets
        log.init_logging()  # NOTE: We run in a subprocess!

        if site_is_local(active_config, site_id):
            automation = AutomationCheckAnalyzeConfig()
            results_data = automation.execute(_TCheckAnalyzeConfig(categories=categories))
        else:
            raw_results_data = do_remote_automation(
                get_site_config(active_config, site_id),
                "check-analyze-config",
                [("categories", json.dumps(categories))],
                timeout=request_.request_timeout - 10,
            )
            assert isinstance(raw_results_data, list)
            results_data = raw_results_data

        logger.debug("[%s] Finished" % site_id)

        result = {
            "state": 0,
            "response": results_data,
        }

    except Exception:
        logger.exception("[%s] Failed" % site_id)
        result = {
            "state": 1,
            "response": "Traceback:<br>%s" % (traceback.format_exc().replace("\n", "<br>\n")),
        }
    finally:
        result_queue.put((site_id, repr(result)))
        result_queue.close()
        result_queue.join_thread()
        result_queue.join()


def _connectivity_result(*, state: ACResultState, text: str, site_id: SiteId) -> ACTestResult:
    return ACTestResult(
        state=state,
        text=text,
        site_id=site_id,
        test_id="ACTestConnectivity",
        category=ACTestCategories.connectivity,
        title=_("Site connectivity"),
        help=_("This check returns CRIT if the connection to the remote site failed."),
    )


def perform_tests(
    logger: logging.Logger,
    active_config: Config,
    request_: Request,
    test_sites: SiteConfigurations,
    categories: Sequence[str] | None = None,  # 'None' means 'No filtering'
) -> dict[SiteId, list[ACTestResult]]:
    logger.debug("Executing tests for %d sites" % len(test_sites))
    results_by_site: dict[SiteId, list[ACTestResult]] = {}

    # Results are fetched simultaneously from the remote sites
    result_queue: multiprocessing.JoinableQueue[tuple[SiteId, str]] = (
        multiprocessing.JoinableQueue()
    )

    processes = []
    site_id = SiteId("unknown_site")
    for site_id in test_sites:
        process = multiprocessing.Process(
            target=_perform_tests_for_site,
            args=(logger, active_config, request_, site_id, categories, result_queue),
        )
        process.start()
        processes.append((site_id, process))

    # Now collect the results from the queue until all processes are finished
    while any(p.is_alive() for site_id, p in processes):
        try:
            site_id, results_data = result_queue.get_nowait()
            result_queue.task_done()
            result = ast.literal_eval(results_data)

            if result["state"] == 1:
                raise MKGeneralException(result["response"])

            if result["state"] == 0:
                test_results = []
                for result_data in result["response"]:
                    result = ACTestResult.from_repr(result_data)
                    test_results.append(result)

                if categories and "connectivity" in categories:
                    # Add general connectivity result
                    test_results.append(
                        _connectivity_result(
                            state=ACResultState.OK,
                            text=_("No connectivity problems"),
                            site_id=site_id,
                        )
                    )

                results_by_site[site_id] = test_results

            else:
                raise NotImplementedError()

        except queue.Empty:
            time.sleep(0.5)  # wait some time to prevent CPU hogs

        except Exception as e:
            if categories and "connectivity" in categories:
                results_by_site[site_id] = [
                    _connectivity_result(
                        state=ACResultState.CRIT,
                        text=str(e),
                        site_id=site_id,
                    )
                ]

            logger.exception("error analyzing configuration for site %s", site_id)

    logger.debug("Got test results")
    return results_by_site
