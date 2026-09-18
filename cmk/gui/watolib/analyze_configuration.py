#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"

"""Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved."""

import ast
import dataclasses
import enum
import json
import logging
import os
import re
import stat
import time
import traceback
from abc import abstractmethod
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from functools import lru_cache
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any, assert_never, Literal, override, Self, TypedDict

import cmk.gui.sites
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import __version__, Version
from cmk.discover_plugins import addons_plugins_local_path, plugins_local_path
from cmk.gui import log
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    make_automation_config,
)
from cmk.gui.watolib.sites import get_effective_global_setting
from cmk.livestatus_client import LocalConnection, SiteConfigurations
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.paths import (
    local_lib_dir,
    local_nagios_plugins_dir,
    local_special_agents_dir,
    local_web_dir,
)
from cmk.utils.statename import short_service_state_name
from cmk.web.utils import escaping


class ACResultState(enum.IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2
    EXCEPTION = 3

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
            case ACResultState.EXCEPTION:
                return f"{self.text} (?)"
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

    @override
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
                    ACResultState.EXCEPTION: "ACResultEXCEPTION",
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
    def title(cls, ident: str) -> str:
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
        raise NotImplementedError

    def title(self) -> str:
        raise NotImplementedError

    def help(self) -> str:
        raise NotImplementedError

    def is_relevant(self) -> bool:
        """A test can check whether or not is relevant for the current evnironment.
        In case this method returns False, the check will not be executed and not
        be shown to the user."""
        raise NotImplementedError

    def execute(self, site_id: SiteId, config: Config) -> Iterator[ACSingleResult]:
        """Implement the test logic here. The method needs to add one or more test
        results like this:

        yield ACResultOK(_("it's fine"))
        """
        raise NotImplementedError

    def run(self, site_id: SiteId, config: Config) -> Iterator[ACTestResult]:
        try:
            for result in self.execute(site_id, config):
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
            gui_logger.exception(
                "Error executing configuration test %(test_name)s: %(traceback)s",
                {
                    "test_name": self.__class__.__name__,
                    "traceback": traceback.format_exc(),
                },
            )
            yield ACTestResult(
                state=ACResultState.EXCEPTION,
                text=(
                    "<pre>%s</pre>"
                    % _("Failed to execute the test %(test_name)s: See web.log for further details")
                    % {"test_name": escaping.escape_attribute(self.__class__.__name__)}
                ),
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

    def _get_effective_global_setting(self, site_id: SiteId, config: Config, varname: str) -> Any:
        return get_effective_global_setting(
            site_id, is_distributed_setup_remote_site(config.sites), varname
        )


class ACTestRegistry(cmk.ccc.plugin_registry.Registry[type[ACTest]]):
    @override
    def plugin_name(self, instance: type[ACTest]) -> str:
        return instance.__name__


ac_test_registry = ACTestRegistry()


class _TCheckAnalyzeConfig(TypedDict):
    site_id: SiteId
    config: Config
    categories: Sequence[str] | None


class AutomationCheckAnalyzeConfig(AutomationCommand[_TCheckAnalyzeConfig]):
    @override
    def command_name(self) -> str:
        return "check-analyze-config"

    @override
    def get_request(self, config: Config, request: Request) -> _TCheckAnalyzeConfig:
        raw_categories = request.get_request().get("categories")
        return _TCheckAnalyzeConfig(
            site_id=omd_site(),
            config=config,
            categories=json.loads(raw_categories) if raw_categories else None,
        )

    @override
    def execute(self, api_request: _TCheckAnalyzeConfig) -> list[ACTestResult]:
        categories = api_request["categories"]
        results: list[ACTestResult] = []
        for test_cls in ac_test_registry.values():
            test = test_cls()

            if categories and test.category() not in categories:
                continue

            if not test.is_relevant():
                continue

            for result in test.run(api_request["site_id"], api_request["config"]):
                results.append(result)

        return results


class _TestResult(TypedDict):
    state: Literal[0, 1]
    ac_test_results: list[ACTestResult]
    error: str


def _perform_tests_for_site(
    logger: logging.Logger,
    config: Config,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    request_: Request,
    site_id: SiteId,
    categories: Sequence[str] | None,
    debug: bool,
) -> _TestResult:
    # Executes the tests on the site. This method is executed in a dedicated
    # thread (One per site)
    logger.debug("[%(site_id)s] Starting", {"site_id": site_id})
    try:
        if isinstance(automation_config, LocalAutomationConfig):
            automation = AutomationCheckAnalyzeConfig()
            ac_test_results = automation.execute(
                _TCheckAnalyzeConfig(
                    site_id=site_id,
                    config=config,
                    categories=categories,
                )
            )
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

        logger.debug(
            "[%(site_id)s] Finished: %(results)r",
            {"site_id": site_id, "results": ac_test_results},
        )
        return _TestResult(
            state=0,
            ac_test_results=ac_test_results,
            error="",
        )

    except Exception:
        logger.exception("[%(site_id)s] Failed", {"site_id": site_id})
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
    config: Config,
    request_: Request,
    test_sites: SiteConfigurations,
    *,
    categories: Sequence[str] | None,  # 'None' means 'No filtering'
    debug: bool,
) -> Mapping[SiteId, Sequence[ACTestResult]]:
    logger.debug("Executing tests for %(num_sites)d sites", {"num_sites": len(test_sites)})
    if not test_sites:
        return {}

    pool = ThreadPool(processes=len(test_sites))

    def run(site_id: SiteId) -> _TestResult:
        return _perform_tests_for_site(
            logger,
            config,
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
                    raise NotImplementedError

            except Exception as e:
                if categories and "connectivity" in categories:
                    results_by_site_id[site_id] = [
                        _connectivity_result(
                            state=ACResultState.CRIT,
                            text=str(e),
                            site_id=site_id,
                        )
                    ]
                logger.exception(
                    "error analyzing configuration for site %(site_id)s", {"site_id": site_id}
                )

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


def try_relative_site_path(site_id: SiteId, abs_path: Path) -> Path:
    try:
        return abs_path.relative_to(Path("/omd/sites", site_id))
    except ValueError:
        # Not a subpath, should not happen
        return abs_path


class ABCACTestPluginAPIs(ACTest):
    """An API which is superseded by a newer one"""

    @property
    @abstractmethod
    def api_name(self) -> str: ...

    @property
    @abstractmethod
    def successor(self) -> str: ...

    @property
    @abstractmethod
    def deprecated_version(self) -> str: ...

    @property
    @abstractmethod
    def removed_version(self) -> str: ...

    @property
    @abstractmethod
    def import_paths(self) -> tuple[str, ...]: ...

    @property
    @abstractmethod
    def content_patterns(self) -> tuple[str, ...]: ...

    def _describe(self) -> str:
        return _(
            "%(api_name)s (deprecated in Checkmk %(deprecated_version)s,"
            " removed in Checkmk %(removed_version)s, use %(successor)s instead)"
        ) % {
            "api_name": self.api_name,
            "deprecated_version": self.deprecated_version,
            "removed_version": self.removed_version,
            "successor": self.successor,
        }

    @override
    def category(self) -> str:
        return ACTestCategories.deprecations

    @override
    def title(self) -> str:
        return _("Outdated plug-in API: %(api_name)s") % {"api_name": self.api_name}

    @override
    def help(self) -> str:
        return _(
            "This API is superseded by a newer one: %(description)s."
            " Checkmk searches the plug-in files below <tt>'%(folders)s'</tt> for its usage."
            " Please migrate the plug-ins to the new API."
        ) % {
            "description": self._describe(),
            "folders": "', '".join(str(r) for r in local_plugin_roots()),
        }

    @override
    def is_relevant(self) -> bool:
        return True

    @override
    def execute(self, site_id: SiteId, config: Config) -> Iterator[ACSingleResult]:
        yield from self.make_outdated_plugin_api_results(site_id, local_plugin_roots())

    def make_outdated_plugin_api_results(
        self, site_id: SiteId, roots: Iterable[Path]
    ) -> Sequence[ACSingleResult]:
        """Report the plug-in files below the given folders which use an outdated API"""
        # Reading and parsing a file is expensive compared to a plain substring search,
        # so only files mentioning one of the searched tokens are inspected further.
        needles = {
            *(_search_needle(module) for module in self.import_paths),
            *self.content_patterns,
        }
        results = [
            self._compute_result(
                used_api=", ".join(sorted(indicators)),
                site_id=site_id,
                path=plugin.path,
            )
            for plugin in _iter_local_plugins(roots, needles)
            if (
                indicators := [
                    *_find_imported_modules(plugin.content, plugin.imports, self.import_paths),
                    *_find_content_patterns(plugin.content, self.content_patterns),
                ]
            )
        ]
        if not results:
            return [
                ACSingleResult(
                    state=ACResultState.OK,
                    text=_("No plug-ins using an outdated API"),
                    site_id=site_id,
                )
            ]
        # 'os.walk' yields the entries in arbitrary order, but the report should be stable.
        return sorted(results, key=lambda result: (str(result.path), result.text))

    def _compute_result(
        self,
        *,
        site_id: SiteId,
        path: Path,
        used_api: str,
    ) -> ACSingleResult:
        base = Version.from_str(__version__).base
        deprecated_base = Version.from_str(self.deprecated_version).base
        removed_base = Version.from_str(self.removed_version).base
        assert base is not None
        assert removed_base is not None
        assert deprecated_base is not None

        # The usage is reported before the deprecation as well, so that users can
        # migrate ahead of time. It only escalates once the timeline is reached.
        if base >= removed_base:
            state = ACResultState.CRIT
            template = _(
                "'%(path)s' uses %(used)s which is deprecated in"
                " Checkmk %(deprecated_version)s and removed in Checkmk %(removed_version)s."
                " Use %(successor)s instead."
            )
        elif base >= deprecated_base:
            state = ACResultState.WARN
            template = _(
                "'%(path)s' uses %(used)s which is deprecated in"
                " Checkmk %(deprecated_version)s and will be removed in Checkmk"
                " %(removed_version)s. Use %(successor)s instead."
            )
        else:
            state = ACResultState.OK
            template = _(
                "'%(path)s' uses %(used)s which will be deprecated in"
                " Checkmk %(deprecated_version)s and removed in Checkmk %(removed_version)s."
                " Use %(successor)s instead."
            )

        return ACSingleResult(
            state=state,
            text=template
            % {
                "path": path,
                # The API name of a test with several import paths does not name them
                # all, so the ones actually found are spelled out in addition.
                "used": (
                    self.api_name if used_api in self.api_name else f"{self.api_name} ({used_api})"
                ),
                "deprecated_version": self.deprecated_version,
                "removed_version": self.removed_version,
                "successor": self.successor,
            },
            site_id=site_id,
            path=path,
        )


# Plug-in files may live next to arbitrary payload (agent binaries, archives, ...).
# Don't read files which are too big to be a plug-in.
MAX_SCANNED_FILE_SIZE = 2 * 1024 * 1024


def local_plugin_roots() -> Iterator[Path]:
    """Yield the folders in which users may place plug-in files"""
    if (cmk_plugins_dir := plugins_local_path()) is not None:
        yield cmk_plugins_dir
    if (cmk_addons_plugins_dir := addons_plugins_local_path()) is not None:
        yield cmk_addons_plugins_dir
    yield local_special_agents_dir
    yield local_nagios_plugins_dir
    yield local_web_dir / "plugins" / "views"
    # Please do NOT rename 'cee': It's the legacy path for bakery plug-ins and is part of MKPs.
    yield local_lib_dir / "python3/cmk/base/cee/plugins/bakery"


@dataclasses.dataclass(frozen=True)
class _LocalPlugin:
    path: Path
    content: str
    imports: set[str] | None


# Compiled Python and shared objects are no plug-in sources, but may well contain the
# searched tokens.
_IGNORED_SUFFIXES = frozenset({".pyc", ".pyo", ".so"})


def _iter_local_plugins(roots: Iterable[Path], needles: Collection[str]) -> Iterator[_LocalPlugin]:
    """Yield the readable text files below the given folders which mention a needle

    Files without a '.py' suffix are included on purpose: special agents and active
    checks are executables which usually don't have any suffix at all.

    Symlinked files are followed, symlinked folders are not (see 'os.walk').
    """
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__" and not d.startswith(".")]
            for filename in filenames:
                path = Path(dirpath, filename)
                if path.suffix in _IGNORED_SUFFIXES:
                    continue
                try:
                    file_stat = path.stat()
                    if (
                        not stat.S_ISREG(file_stat.st_mode)
                        or file_stat.st_size > MAX_SCANNED_FILE_SIZE
                    ):
                        continue
                    content = path.read_text(encoding="utf-8")
                except OSError, UnicodeDecodeError:
                    continue
                if not any(needle in content for needle in needles):
                    continue
                yield _LocalPlugin(
                    path=path, content=content, imports=_parse_imported_names(content)
                )


# A version component such as 'v1' is no useful needle: it occurs in nearly every
# plug-in file, which would defeat the substring prefilter entirely.
_VERSION_COMPONENT = re.compile(r"^v\d")


def _search_needle(module: str) -> str:
    """Return the substring which every import of the given module must contain

    Only a single component is searched: it is the only part which is guaranteed to
    occur, be it imported from its parent package ('from cmk.bakery import v1') or
    relatively ('from . import bakery_api'). Trailing version components are skipped
    in favour of the component which actually names the API.
    """
    components = module.split(".")
    while len(components) > 1 and _VERSION_COMPONENT.match(components[-1]):
        components.pop()
    return components[-1]


@lru_cache
def _import_pattern(module: str) -> re.Pattern[str]:
    """Compile a pattern matching the import statements of the given module

    A module starting with a dot is matched as the corresponding relative import.
    """
    name = re.escape(module)
    alternatives = [
        # 'from cmk.utils.password_store import ...', submodules included
        rf"from[ \t]+{name}(?:\.\S+)?[ \t]+import[ \t]",
        # 'import cmk.utils.password_store', submodules and further modules included
        rf"import[ \t]+{name}(?:\.\S+)?(?:[ \t,]|$)",
    ]
    parent, separator, leaf = module.rpartition(".")
    if separator:
        # 'from cmk.utils import password_store', 'from . import bakery_api'
        alternatives.append(
            rf"from[ \t]+{re.escape(parent) if parent else re.escape('.')}[ \t]+import[ \t]+"
            rf"(?:[^\n]*[ \t(,])?{re.escape(leaf)}\b"
        )
    return re.compile(rf"^[ \t]*(?:{'|'.join(alternatives)})", re.MULTILINE)


def _parse_imported_names(content: str) -> set[str] | None:
    """Return the modules and objects imported by the given Python source

    None is returned if the content is no valid Python: plug-in folders may contain
    shell scripts, agent binaries and other payload.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError, ValueError, RecursionError:
        return None

    names: set[str] = set()
    for node in ast.walk(tree):
        match node:
            case ast.Import():
                names.update(alias.name for alias in node.names)
            case ast.ImportFrom():
                # 'from . import foo' has no module, 'from .foo import bar' has no dots
                module = "." * node.level + (node.module or "")
                separator = "" if module.endswith(".") else "."
                names.update(f"{module}{separator}{alias.name}" for alias in node.names)
            case _:
                pass
    return names


def _find_imported_modules(
    content: str, imported: set[str] | None, modules: Iterable[str]
) -> set[str]:
    r"""Return those of the modules which are imported by the given file content

    'imported' are the names parsed from the content, or None if it is no valid
    Python. Modules which merely share a prefix are never matched, and a module
    starting with a dot matches the corresponding relative import.

    Mentions in comments or strings are ignored as long as the content could be
    parsed. The textual fallback below cannot tell code from a string: it matches
    any line starting with a matching import statement, including one inside a
    docstring or a heredoc.
    """
    if imported is None:
        # Fall back to a textual search, so that at least the imports of a plug-in
        # which we cannot parse are reported. Continuation lines are not matched.
        return {module for module in modules if _import_pattern(module).search(content)}

    return {
        module
        for module in modules
        if any(name == module or name.startswith(f"{module}.") for name in imported)
    }


def _find_content_patterns(content: str, markers: Iterable[str]) -> set[str]:
    """Return those markers that are found in the given file content"""
    return {m for m in markers if m in content}
