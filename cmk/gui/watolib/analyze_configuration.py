#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved."""

import traceback
from typing import (  # pylint: disable=unused-import
    Type, Iterator, Text, Optional, List, Any,
)

from livestatus import LocalConnection
import cmk.utils.defines

import cmk.gui.sites
import cmk.gui.config as config
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.exceptions import MKGeneralException

from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.sites import SiteManagementFactory
from cmk.gui.plugins.watolib.utils import ABCConfigDomain
from cmk.gui.watolib.automation_commands import (
    AutomationCommand,
    automation_command_registry,
)


class ACResult(object):
    status = None  # type: Optional[int]

    def __init__(self, text):
        super(ACResult, self).__init__()
        self.text = text
        self.site_id = config.omd_site()

    def from_test(self, test):
        self.test_id = test.id()
        self.category = test.category()
        self.title = test.title()
        self.help = test.help()

    @classmethod
    def merge(cls, *results):
        """Create a new result object from the given result objects.

        a) use the worst state
        b) concatenate the texts
        """
        texts, worst_cls = [], ACResultOK
        for result in results:
            text = result.text
            if result.status != 0:
                text += " (%s)" % ("!" * result.status)
            texts.append(text)

            if result.status > worst_cls.status:
                worst_cls = result.__class__

        return worst_cls(", ".join(texts))

    def status_name(self):
        return cmk.utils.defines.short_service_state_name(self.status)

    @classmethod
    def from_repr(cls, repr_data):
        result_class_name = repr_data.pop("class_name")
        result = globals()[result_class_name](repr_data["text"])

        for key, val in repr_data.items():
            setattr(result, key, val)

        return result

    def __repr__(self):
        return repr({
            "site_id": self.site_id,
            "class_name": self.__class__.__name__,
            "text": self.text,
            # These fields are be static - at least for the current version, but
            # we transfer them to the central system to be able to handle test
            # results of tests not known to the central site.
            "test_id": self.test_id,
            "category": self.category,
            "title": self.title,
            "help": self.help,
        })


class ACResultNone(ACResult):
    status = -1


class ACResultCRIT(ACResult):
    status = 2


class ACResultWARN(ACResult):
    status = 1


class ACResultOK(ACResult):
    status = 0


class ACTestCategories(object):
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


class ACTest(object):
    def __init__(self):
        # type: () -> None
        self._executed = False
        self._results = []  # type: List[ACResult]

    def id(self):
        # type: () -> str
        return self.__class__.__name__

    def category(self):
        # type: () -> str
        """Return the internal name of the category the BP test is associated with"""
        raise NotImplementedError()

    def title(self):
        # type: () -> Text
        raise NotImplementedError()

    def help(self):
        # type: () -> Text
        raise NotImplementedError()

    def is_relevant(self):
        # type: () -> bool
        """A test can check whether or not is relevant for the current evnironment.
        In case this method returns False, the check will not be executed and not
        be shown to the user."""
        raise NotImplementedError()

    def execute(self):
        # type: () -> Iterator[ACResult]
        """Implement the test logic here. The method needs to add one or more test
        results like this:

        yield ACResultOK(_("it's fine"))
        """
        raise NotImplementedError()

    def run(self):
        # type: () -> Iterator[ACResult]
        self._executed = True
        try:
            # Do not merge results that have been gathered on one site for different sites
            results = list(self.execute())
            num_sites = len(set(r.site_id for r in results))
            if num_sites > 1:
                for result in results:
                    result.from_test(self)
                    yield result
                return

            # Merge multiple results produced for a single site
            total_result = ACResult.merge(*list(self.execute()))
            total_result.from_test(self)
            yield total_result
        except Exception:
            logger.exception("error executing configuration test %s", self.__class__.__name__)
            result = ACResultCRIT(
                "<pre>%s</pre>" % _("Failed to execute the test %s: %s") %
                (escaping.escape_attribute(self.__class__.__name__), traceback.format_exc()))
            result.from_test(self)
            yield result

    def status(self):
        # type: () -> int
        return max([0] + [(r.status or 0) for r in self.results])

    def status_name(self):
        # type: () -> Text
        return cmk.utils.defines.short_service_state_name(self.status())

    @property
    def results(self):
        # type: () -> List[ACResult]
        if not self._executed:
            raise MKGeneralException(_("The test has not been executed yet"))
        return self._results

    def _uses_microcore(self):
        # type: () -> bool
        """Whether or not the local site is using the CMC"""
        local_connection = LocalConnection()
        version = local_connection.query_value("GET status\nColumns: program_version\n", deflt="")
        return version.startswith("Check_MK")

    def _get_effective_global_setting(self, varname):
        # type: (str) -> Any
        global_settings = load_configuration_settings()
        default_values = ABCConfigDomain.get_all_default_globals()

        if cmk.gui.config.is_wato_slave_site():
            current_settings = load_configuration_settings(site_specific=True)
        else:
            sites = SiteManagementFactory.factory().load_sites()
            current_settings = sites[config.omd_site()].get("globals", {})

        if varname in current_settings:
            value = current_settings[varname]
        elif varname in global_settings:
            value = global_settings[varname]
        else:
            value = default_values[varname]

        return value


class ACTestRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        # type: () -> Type[ACTest]
        return ACTest

    def plugin_name(self, plugin_class):
        # type: (Type[ACTest]) -> str
        return plugin_class.__name__


ac_test_registry = ACTestRegistry()


@automation_command_registry.register
class AutomationCheckAnalyzeConfig(AutomationCommand):
    def command_name(self):
        # type: () -> str
        return "check-analyze-config"

    def get_request(self):
        # type: () -> None
        return None

    def execute(self, _unused_request):
        # type: (None) -> List[ACResult]
        results = []  # type: List[ACResult]
        for test_cls in ac_test_registry.values():
            test = test_cls()

            if not test.is_relevant():
                continue

            for result in test.run():
                results.append(result)

        return results
