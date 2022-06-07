#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved.
"""

import ast
import multiprocessing
import queue
import time
import traceback
from typing import Any, Collection, Dict, Tuple

from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.log as log
import cmk.gui.utils.escaping as escaping
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import MKGeneralException, MKUserError
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
from cmk.gui.plugins.wato.utils import mode_registry, WatoMode
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri
from cmk.gui.watolib.analyze_configuration import (
    ac_test_registry,
    ACResult,
    ACResultCRIT,
    ACResultOK,
    ACTest,
    ACTestCategories,
    AutomationCheckAnalyzeConfig,
)
from cmk.gui.watolib.automations import do_remote_automation


@ac_test_registry.register
class ACTestConnectivity(ACTest):
    def category(self) -> str:
        return ACTestCategories.connectivity

    def title(self) -> str:
        return _("Site connectivity")

    def help(self) -> str:
        return _("This check returns CRIT if the connection to the remote site failed.")

    def is_relevant(self) -> bool:
        # This test is always irrelevant :)
        return False


@mode_registry.register
class ModeAnalyzeConfig(WatoMode):
    _ack_path = cmk.utils.paths.var_dir + "/acknowledged_bp_tests.mk"

    @classmethod
    def name(cls) -> str:
        return "analyze_config"

    @classmethod
    def permissions(cls) -> Collection[PermissionName]:
        return []

    def __init__(self) -> None:
        super().__init__()
        self._logger = logger.getChild("analyze-config")
        self._acks = self._load_acknowledgements()

    def _from_vars(self):
        self._show_ok = request.has_var("show_ok")
        self._show_failed = not request.has_var("hide_failed")
        self._show_ack = request.has_var("show_ack")

    def title(self) -> str:
        return _("Analyze configuration")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
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

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return None

        test_id = request.var("_test_id")
        site_id = request.var("_site_id")
        status_id = request.get_integer_input_mandatory("_status_id", 0)

        if not test_id:
            raise MKUserError("_ack_test_id", _("Needed variable missing"))

        if request.var("_do") in ["ack", "unack"]:
            if not site_id:
                raise MKUserError("_ack_site_id", _("Needed variable missing"))

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
                    "distributed WATO slave sites. You currently have no such site configured."
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

                for test_id, test_results_by_site in sorted(
                    results_by_test.items(), key=lambda x: x[1]["test"]["title"]
                ):
                    self._show_test_row(table, test_id, test_results_by_site, site_ids)

    def _show_test_row(  # pylint: disable=too-many-branches
        self,
        table,
        test_id,
        test_results_by_site,
        site_ids,
    ):
        table.row()

        table.cell(_("Actions"), css="buttons", sortable=False)
        html.icon_button(
            None,
            _("Toggle result details"),
            "toggle_details",
            onclick="cmk.wato.toggle_container('test_result_details_%s')" % test_id,
        )

        worst_result = sorted(
            test_results_by_site["site_results"].values(), key=lambda result: result.status
        )[0]

        # Disabling of test in total
        is_test_disabled = self._is_test_disabled(test_id)
        if is_test_disabled:
            html.icon_button(
                makeactionuri(
                    request,
                    transactions,
                    [
                        ("_do", "enable"),
                        ("_test_id", worst_result.test_id),
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
                        ("_test_id", worst_result.test_id),
                    ],
                ),
                _("Disable this test"),
                "disable_test",
            )

        # assume all have the same test meta information (title, help, ...)
        table.cell(_("Title"), css="title " + "stale" if is_test_disabled else "")
        html.write_text(test_results_by_site["test"]["title"])

        # Now loop all sites to display their results
        for site_id in site_ids:
            if is_test_disabled:
                table.cell(site_id, "")
                table.cell("", "")
                continue

            result = test_results_by_site["site_results"].get(site_id)
            if result is None:
                table.cell(site_id, css="state state-1")
                table.cell("", css="buttons")
                continue

            is_acknowledged = self._is_acknowledged(result)

            if is_acknowledged or result.status == -1:
                css = "state stale"
            else:
                css = "state state%d" % result.status

            table.cell(site_id, css=css)
            html.span(result.status_name(), title=result.text, class_="state_rounded_fill")

            table.cell("", css="buttons")

            if result.status != 0:
                if is_acknowledged:
                    html.icon_button(
                        makeactionuri(
                            request,
                            transactions,
                            [
                                ("_do", "unack"),
                                ("_site_id", result.site_id),
                                ("_status_id", result.status),
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
                                ("_status_id", result.status),
                                ("_test_id", result.test_id),
                            ],
                        ),
                        _("Acknowledge this test result for site %s") % site_id,
                        "acknowledge_test",
                    )
            else:
                html.write_text("")

        # Add toggleable notitication context
        table.row(css="ac_test_details hidden", id_="test_result_details_%s" % test_id)
        table.cell(colspan=2 + 2 * len(site_ids))

        html.write_text(test_results_by_site["test"]["help"])

        if not is_test_disabled:
            html.open_table()
            for site_id in site_ids:
                result = test_results_by_site["site_results"].get(site_id)
                if result is None:
                    continue

                html.open_tr()
                html.td(escaping.escape_attribute(site_id))
                html.td("%s: %s" % (result.status_name(), result.text))
                html.close_tr()
            html.close_table()

        # This dummy row is needed for not destroying the odd/even row highlighting
        table.row(css="hidden")

    def _perform_tests(self):
        test_sites = self._analyze_sites()

        self._logger.debug("Executing tests for %d sites" % len(test_sites))
        results_by_site = {}

        # Results are fetched simultaneously from the remote sites
        result_queue: multiprocessing.Queue[Tuple[SiteId, str]] = multiprocessing.JoinableQueue()

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
                        result = ACResult.from_repr(result_data)
                        test_results.append(result)

                    # Add general connectivity result
                    result = ACResultOK(_("No connectivity problems"))
                    result.from_test(ACTestConnectivity())
                    result.site_id = site_id
                    test_results.append(result)

                    results_by_site[site_id] = test_results

                else:
                    raise NotImplementedError()

            except queue.Empty:
                time.sleep(0.5)  # wait some time to prevent CPU hogs

            except Exception as e:
                result = ACResultCRIT("%s" % e)
                result.from_test(ACTestConnectivity())
                result.site_id = site_id
                results_by_site[site_id] = [result]

                logger.exception("error analyzing configuration for site %s", site_id)

        self._logger.debug("Got test results")

        # Group results by category in first instance and then then by test
        results_by_category: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for site_id, results in results_by_site.items():
            for result in results:
                category_results = results_by_category.setdefault(result.category, {})
                test_results_by_site = category_results.setdefault(
                    result.test_id,
                    {
                        "site_results": {},
                        "test": {
                            "title": result.title,
                            "help": result.help,
                        },
                    },
                )

                test_results_by_site["site_results"][result.site_id] = result

        return results_by_category

    def _analyze_sites(self):
        return activation_sites()

    # Executes the tests on the site. This method is executed in a dedicated
    # subprocess (One per site)
    def _perform_tests_for_site(
        self, site_id: SiteId, result_queue: "multiprocessing.Queue[Tuple[SiteId, str]]"
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

            if site_is_local(site_id):
                automation = AutomationCheckAnalyzeConfig()
                results_data = automation.execute(automation.get_request())

            else:
                results_data = do_remote_automation(
                    get_site_config(site_id),
                    "check-analyze-config",
                    [],
                    timeout=request.request_timeout - 10,
                )

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

    def _is_acknowledged(self, result):
        return (result.test_id, result.site_id, result.status) in self._acks

    def _is_test_disabled(self, test_id):
        return not self._acks.get(test_id, True)

    def _unacknowledge_test(self, test_id, site_id, status_id):
        self._acks = self._load_acknowledgements(lock=True)
        try:
            del self._acks[(test_id, site_id, status_id)]
            self._save_acknowledgements(self._acks)
        except KeyError:
            pass

    def _acknowledge_test(self, test_id, site_id, status_id):
        self._acks = self._load_acknowledgements(lock=True)
        self._acks[(test_id, site_id, status_id)] = {
            "user_id": user.id,
            "time": time.time(),
        }
        self._save_acknowledgements(self._acks)

    def _enable_test(self, test_id, enabling=True):
        self._acks = self._load_acknowledgements(lock=True)
        self._acks[(test_id)] = enabling
        self._save_acknowledgements(self._acks)

    def _disable_test(self, test_id):
        self._enable_test(test_id, False)

    def _save_acknowledgements(self, acknowledged_werks):
        store.save_object_to_file(self._ack_path, acknowledged_werks)

    def _load_acknowledgements(self, lock=False):
        return store.load_object_from_file(self._ack_path, default={}, lock=lock)
