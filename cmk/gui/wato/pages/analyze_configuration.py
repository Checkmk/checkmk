#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved.
"""

from __future__ import annotations

import ast
import dataclasses
import multiprocessing
import queue
import time
import traceback
from collections.abc import Collection

from livestatus import SiteConfigurations, SiteId

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.paths

from cmk.gui import log
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import escaping
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import DocReference, makeactionuri
from cmk.gui.watolib.analyze_configuration import (
    ACResultState,
    ACTestCategories,
    ACTestResult,
    AutomationCheckAnalyzeConfig,
)
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.mode import ModeRegistry, WatoMode


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeAnalyzeConfig)


class ModeAnalyzeConfig(WatoMode):
    _ack_path = cmk.utils.paths.var_dir + "/acknowledged_bp_tests.mk"

    @classmethod
    def name(cls) -> str:
        return "analyze_config"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    def __init__(self) -> None:
        super().__init__()
        self._logger = logger.getChild("analyze-config")
        self._acks = self._load_acknowledgements()

    def _from_vars(self) -> None:
        self._show_ok = request.has_var("show_ok")
        self._show_failed = not request.has_var("hide_failed")
        self._show_ack = request.has_var("show_ack")

    def title(self) -> str:
        return _("Analyze configuration")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Configure"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Support diagnostics"),
                                    icon_name="diagnostics",
                                    item=make_simple_link("wato.py?mode=diagnostics"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        menu.add_doc_reference(
            _("Analyzing the Checkmk site configuration"), DocReference.ANALYZE_CONFIG
        )
        return menu

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return None

        test_id = request.get_str_input_mandatory("_test_id")
        status_id = request.get_integer_input_mandatory("_status_id", 0)

        if request.var("_do") in ["ack", "unack"]:
            site_id = SiteId(request.get_str_input_mandatory("_site_id"))

            if site_id not in activation_sites():
                raise MKUserError("_ack_site_id", _("Invalid site given"))

            if request.var("_do") == "ack":
                self._acknowledge_test(test_id, site_id, status_id)

            elif request.var("_do") == "unack":
                self._unacknowledge_test(test_id, site_id, status_id)

        elif request.var("_do") == "disable":
            self._disable_test(test_id)

        elif request.var("_do") == "enable":
            self._enable_test(test_id)

        else:
            raise NotImplementedError()

        return None

    def page(self) -> None:
        if not self._analyze_sites():
            html.show_message(
                _(
                    "Analyze configuration can only be used with the local site and "
                    "distributed setup remote sites. You currently have no such site configured."
                )
            )
            return

        results_by_category = self._perform_tests()

        site_ids = sorted(self._analyze_sites())

        for category_name, results_by_test in sorted(
            results_by_category.items(), key=lambda x: ACTestCategories.title(x[0])
        ):
            with table_element(
                title=ACTestCategories.title(category_name),
                css="data analyze_config",
                sortable=False,
                searchable=False,
            ) as table:
                for test_id, row_data in sorted(results_by_test.items(), key=lambda x: x[1].title):
                    self._show_test_row(table, test_id, row_data, site_ids)

    def _show_test_row(
        self,
        table: Table,
        test_id: str,
        row_data: _TestResult,
        site_ids: Collection[SiteId],
    ) -> None:
        table.row()

        table.cell(_("Actions"), css=["buttons"], sortable=False)
        html.icon_button(
            None,
            _("Toggle result details"),
            "toggle_details",
            onclick="cmk.wato.toggle_container('test_result_details_%s')" % test_id,
        )

        # Disabling of test in total
        is_test_disabled = self._is_test_disabled(test_id)
        if is_test_disabled:
            html.icon_button(
                makeactionuri(
                    request,
                    transactions,
                    [
                        ("_do", "enable"),
                        ("_test_id", test_id),
                    ],
                ),
                _("Reenable this test"),
                "enable_test",
            )
        else:
            html.icon_button(
                makeactionuri(
                    request,
                    transactions,
                    [
                        ("_do", "disable"),
                        ("_test_id", test_id),
                    ],
                ),
                _("Disable this test"),
                "disable_test",
            )

        # assume all have the same test meta information (title, help, ...)
        table.cell(_("Title"), css=["title"] + ["stale"] if is_test_disabled else [])
        html.write_text_permissive(row_data.title)

        # Now loop all sites to display their results
        for site_id in site_ids:
            if is_test_disabled:
                table.cell(site_id, "")
                table.cell("", "")
                continue

            result = row_data.results_by_site.get(site_id)
            if result is None:
                table.cell(site_id, css=["state", "state-1"])
                table.cell("", css=["buttons"])
                continue

            is_acknowledged = self._is_acknowledged(result)

            if is_acknowledged:
                css = ["state", "stale"]
            else:
                css = ["state", "state%d" % result.state.value]

            table.cell(site_id, css=css)
            html.span(result.state.short_name, title=result.text, class_="state_rounded_fill")

            table.cell("", css=["buttons"])

            if result.state is not ACResultState.OK:
                if is_acknowledged:
                    html.icon_button(
                        makeactionuri(
                            request,
                            transactions,
                            [
                                ("_do", "unack"),
                                ("_site_id", result.site_id),
                                ("_status_id", result.state.value),
                                ("_test_id", result.test_id),
                            ],
                        ),
                        _("Unacknowledge this test result for site %s") % site_id,
                        "unacknowledge_test",
                    )
                else:
                    html.icon_button(
                        makeactionuri(
                            request,
                            transactions,
                            [
                                ("_do", "ack"),
                                ("_site_id", result.site_id),
                                ("_status_id", result.state.value),
                                ("_test_id", result.test_id),
                            ],
                        ),
                        _("Acknowledge this test result for site %s") % site_id,
                        "acknowledge_test",
                    )
            else:
                html.write_text_permissive("")

        # Add toggleable notitication context
        table.row(css=["ac_test_details", "hidden"], id_="test_result_details_%s" % test_id)
        table.cell(colspan=2 + 2 * len(site_ids))

        html.write_text_permissive(row_data.help)

        if not is_test_disabled:
            html.open_table()
            for site_id in site_ids:
                result = row_data.results_by_site.get(site_id)
                if result is None:
                    continue

                html.open_tr()
                html.td(escaping.escape_attribute(site_id))
                html.td(f"{result.state.short_name}: {result.text}")
                html.close_tr()
            html.close_table()

        # This dummy row is needed for not destroying the odd/even row highlighting
        table.row(css=["hidden"])

    def _perform_tests(self) -> dict[str, dict[str, _TestResult]]:
        test_sites = self._analyze_sites()

        self._logger.debug("Executing tests for %d sites" % len(test_sites))
        results_by_site: dict[SiteId, list[ACTestResult]] = {}

        # Results are fetched simultaneously from the remote sites
        result_queue: multiprocessing.JoinableQueue[tuple[SiteId, str]] = (
            multiprocessing.JoinableQueue()
        )

        processes = []
        site_id = SiteId("unknown_site")
        for site_id in test_sites:
            process = multiprocessing.Process(
                target=self._perform_tests_for_site, args=(site_id, result_queue)
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
                results_by_site[site_id] = [
                    _connectivity_result(
                        state=ACResultState.CRIT,
                        text=str(e),
                        site_id=site_id,
                    )
                ]

                logger.exception("error analyzing configuration for site %s", site_id)

        self._logger.debug("Got test results")

        # Group results by category in first instance and then then by test
        results_by_category: dict[str, dict[str, _TestResult]] = {}
        for site_id, results in results_by_site.items():
            for result in results:
                category_results = results_by_category.setdefault(result.category, {})
                row_data = category_results.setdefault(
                    result.test_id,
                    _TestResult(
                        results_by_site={},
                        title=result.title,
                        help=result.help,
                    ),
                )

                row_data.results_by_site[result.site_id] = result

        return results_by_category

    def _analyze_sites(self) -> SiteConfigurations:
        return activation_sites()

    # Executes the tests on the site. This method is executed in a dedicated
    # subprocess (One per site)
    def _perform_tests_for_site(
        self, site_id: SiteId, result_queue: multiprocessing.JoinableQueue[tuple[SiteId, str]]
    ) -> None:
        self._logger.debug("[%s] Starting" % site_id)
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
                # NOTE: The mypy people are too stubborn to fix this, see https://github.com/python/mypy/issues/6549
                results_data = automation.execute(automation.get_request())  # type: ignore[func-returns-value]

            else:
                raw_results_data = do_remote_automation(
                    get_site_config(active_config, site_id),
                    "check-analyze-config",
                    [],
                    timeout=request.request_timeout - 10,
                )
                assert isinstance(raw_results_data, list)
                results_data = raw_results_data

            self._logger.debug("[%s] Finished" % site_id)

            result = {
                "state": 0,
                "response": results_data,
            }

        except Exception:
            self._logger.exception("[%s] Failed" % site_id)
            result = {
                "state": 1,
                "response": "Traceback:<br>%s" % (traceback.format_exc().replace("\n", "<br>\n")),
            }
        finally:
            result_queue.put((site_id, repr(result)))
            result_queue.close()
            result_queue.join_thread()
            result_queue.join()

    def _is_acknowledged(self, result: ACTestResult) -> bool:
        return (result.test_id, result.site_id, result.state.value) in self._acks

    def _is_test_disabled(self, test_id: str) -> bool:
        return not self._acks.get(test_id, True)

    def _unacknowledge_test(self, test_id: str, site_id: SiteId, status_id: int) -> None:
        self._acks = self._load_acknowledgements(lock=True)
        try:
            del self._acks[(test_id, site_id, status_id)]
            self._save_acknowledgements(self._acks)
        except KeyError:
            pass

    def _acknowledge_test(self, test_id: str, site_id: SiteId, status_id: int) -> None:
        self._acks = self._load_acknowledgements(lock=True)
        self._acks[(test_id, site_id, status_id)] = {
            "user_id": user.id,
            "time": time.time(),
        }
        self._save_acknowledgements(self._acks)

    def _enable_test(self, test_id: str, enabling: bool = True) -> None:
        self._acks = self._load_acknowledgements(lock=True)
        self._acks[(test_id)] = enabling
        self._save_acknowledgements(self._acks)

    def _disable_test(self, test_id: str) -> None:
        self._enable_test(test_id, False)

    def _save_acknowledgements(self, acknowledgements: dict[object, object]) -> None:
        store.save_object_to_file(self._ack_path, acknowledgements)

    def _load_acknowledgements(self, lock: bool = False) -> dict[object, object]:
        return store.load_object_from_file(self._ack_path, default={}, lock=lock)


@dataclasses.dataclass(frozen=True)
class _TestResult:
    results_by_site: dict[SiteId, ACTestResult]
    title: str
    help: str


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
