#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved."""

import dataclasses
import enum
import traceback
from collections.abc import Iterable, Iterator, Mapping
from typing import Any, assert_never, Self

from livestatus import LocalConnection, SiteId

from cmk.ccc.site import omd_site

from cmk.utils.statename import short_service_state_name

import cmk.gui.sites
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.utils import escaping
from cmk.gui.watolib.automation_commands import AutomationCommand
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
    site_id: SiteId = dataclasses.field(default_factory=omd_site)

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
    site_id: SiteId = dataclasses.field(default_factory=omd_site)

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
            )
        except Exception:
            logger.exception("error executing configuration test %s", self.__class__.__name__)
            yield ACTestResult(
                state=ACResultState.CRIT,
                text="<pre>%s</pre>"
                % _("Failed to execute the test %s: %s")
                % (escaping.escape_attribute(self.__class__.__name__), traceback.format_exc()),
                test_id=self.id(),
                category=self.category(),
                title=self.title(),
                help=self.help(),
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


class AutomationCheckAnalyzeConfig(AutomationCommand[None]):
    def command_name(self) -> str:
        return "check-analyze-config"

    def get_request(self) -> None:
        return None

    def execute(self, _unused_request: None) -> list[ACTestResult]:
        results: list[ACTestResult] = []
        for test_cls in ac_test_registry.values():
            test = test_cls()

            if not test.is_relevant():
                continue

            for result in test.run():
                results.append(result)

        return results
