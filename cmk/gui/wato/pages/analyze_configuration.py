#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""
Provides the user with hints about his setup. Performs different
checks and tells the user what could be improved.
"""

import time
import multiprocessing
import Queue
import traceback
import ast

import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.watolib as watolib
import cmk.gui.config as config
from cmk.gui.table import table_element
import cmk.gui.log as log
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.globals import html

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)

from cmk.gui.watolib.changes import activation_sites
from cmk.gui.watolib.analyze_configuration import (
    ACResult,
    ACTestCategories,
    AutomationCheckAnalyzeConfig,
)


@mode_registry.register
class ModeAnalyzeConfig(WatoMode):
    _ack_path = cmk.utils.paths.var_dir + "/acknowledged_bp_tests.mk"

    @classmethod
    def name(cls):
        return "analyze_config"

    @classmethod
    def permissions(cls):
        return []

    def __init__(self):
        super(ModeAnalyzeConfig, self).__init__()
        self._logger = logger.getChild("analyze-config")
        self._acks = self._load_acknowledgements()

    def _from_vars(self):
        self._show_ok = html.request.has_var("show_ok")
        self._show_failed = not html.request.has_var("hide_failed")
        self._show_ack = html.request.has_var("show_ack")

    def title(self):
        return _("Analyze configuration")

    def action(self):
        if not html.check_transaction():
            return

        test_id = html.request.var("_test_id")
        site_id = html.request.var("_site_id")
        status_id = html.get_integer_input("_status_id", 0)

        if not test_id:
            raise MKUserError("_ack_test_id", _("Needed variable missing"))

        if html.request.var("_do") in ["ack", "unack"]:
            if not site_id:
                raise MKUserError("_ack_site_id", _("Needed variable missing"))

            if site_id not in activation_sites():
                raise MKUserError("_ack_site_id", _("Invalid site given"))

        if html.request.var("_do") == "ack":
            self._acknowledge_test(test_id, site_id, status_id)

        elif html.request.var("_do") == "unack":
            self._unacknowledge_test(test_id, site_id, status_id)

        elif html.request.var("_do") == "disable":
            self._disable_test(test_id)

        elif html.request.var("_do") == "enable":
            self._enable_test(test_id)

        else:
            raise NotImplementedError()

    def page(self):
        if not self._analyze_sites():
            html.show_info(
                _("Analyze configuration can only be used with the local site and "
                  "distributed WATO slave sites. You currently have no such site configured."))
            return

        results_by_category = self._perform_tests()

        site_ids = sorted(self._analyze_sites())

        for category_name, results_by_test in sorted(results_by_category.items(),
                                                     key=lambda x: ACTestCategories.title(x[0])):
            with table_element(title=ACTestCategories.title(category_name),
                               css="data analyze_config",
                               sortable=False,
                               searchable=False) as table:

                for test_id, test_results_by_site in sorted(results_by_test.items(),
                                                            key=lambda x: x[1]["test"]["title"]):
                    self._show_test_row(table, test_id, test_results_by_site, site_ids)

    def _show_test_row(self, table, test_id, test_results_by_site, site_ids):
        table.row()

        table.cell(_("Actions"), css="buttons", sortable=False)
        html.icon_button(None,
                         _("Toggle result details"),
                         "toggle_details",
                         onclick="cmk.wato.toggle_container('test_result_details_%s')" % test_id)

        worst_result = sorted(test_results_by_site["site_results"].values(),
                              key=lambda result: result.status)[0]

        # Disabling of test in total
        is_test_disabled = self._is_test_disabled(test_id)
        if is_test_disabled:
            html.icon_button(
                html.makeactionuri([
                    ("_do", "enable"),
                    ("_test_id", worst_result.test_id),
                ]),
                _("Reenable this test"),
                "enable_test",
            )
        else:
            html.icon_button(
                html.makeactionuri([
                    ("_do", "disable"),
                    ("_test_id", worst_result.test_id),
                ]),
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
            html.open_div(title=result.text)
            html.write_text(result.status_name())
            html.close_div()

            table.cell("", css="buttons")

            if result.status != 0:
                if is_acknowledged:
                    html.icon_button(
                        html.makeactionuri([
                            ("_do", "unack"),
                            ("_site_id", result.site_id),
                            ("_status_id", result.status),
                            ("_test_id", result.test_id),
                        ]),
                        _("Unacknowledge this test result for site %s") % site_id,
                        "unacknowledge_test",
                    )
                else:
                    html.icon_button(
                        html.makeactionuri([
                            ("_do", "ack"),
                            ("_site_id", result.site_id),
                            ("_status_id", result.status),
                            ("_test_id", result.test_id),
                        ]),
                        _("Acknowledge this test result for site %s") % site_id,
                        "acknowledge_test",
                    )
            else:
                html.write("")

        # Add toggleable notitication context
        table.row(class_="ac_test_details hidden", id_="test_result_details_%s" % test_id)
        table.cell(colspan=2 + 2 * len(site_ids))

        html.write_text(test_results_by_site["test"]["help"])

        if not is_test_disabled:
            html.open_table()
            for site_id in site_ids:
                result = test_results_by_site["site_results"].get(site_id)
                if result is None:
                    continue

                html.open_tr()
                html.td(html.attrencode(site_id))
                html.td("%s: %s" % (result.status_name(), result.text))
                html.close_tr()
            html.close_table()

        # This dummy row is needed for not destroying the odd/even row highlighting
        table.row(class_="hidden")

    def _perform_tests(self):
        test_sites = self._analyze_sites()

        self._logger.debug("Executing tests for %d sites" % len(test_sites))
        results_by_site = {}

        # Results are fetched simultaneously from the remote sites
        result_queue = multiprocessing.JoinableQueue()

        processes = []
        for site_id in test_sites:
            process = multiprocessing.Process(target=self._perform_tests_for_site,
                                              args=(site_id, result_queue))
            process.start()
            processes.append((site_id, process))

        # Now collect the results from the queue until all processes are finished
        while any([p.is_alive() for site_id, p in processes]):
            try:
                site_id, results_data = result_queue.get_nowait()
                result_queue.task_done()
                result = ast.literal_eval(results_data)

                if result["state"] == 1:
                    raise MKGeneralException(result["response"])

                elif result["state"] == 0:
                    test_results = []
                    for result_data in result["response"]:
                        result = ACResult.from_repr(result_data)
                        test_results.append(result)

                    results_by_site[site_id] = test_results

                else:
                    raise NotImplementedError()

            except Queue.Empty:
                time.sleep(0.5)  # wait some time to prevent CPU hogs

            except Exception as e:
                logger.exception("error analyzing configuration for site %s", site_id)
                html.show_error("%s: %s" % (site_id, e))

        self._logger.debug("Got test results")

        # Group results by category in first instance and then then by test
        results_by_category = {}
        for site_id, results in results_by_site.items():
            for result in results:
                category_results = results_by_category.setdefault(result.category, {})
                test_results_by_site = category_results.setdefault(result.test_id, {
                    "site_results": {},
                    "test": {
                        "title": result.title,
                        "help": result.help,
                    }
                })

                test_results_by_site["site_results"][result.site_id] = result

        return results_by_category

    def _analyze_sites(self):
        return activation_sites()

    # Executes the tests on the site. This method is executed in a dedicated
    # subprocess (One per site)
    def _perform_tests_for_site(self, site_id, result_queue):
        self._logger.debug("[%s] Starting" % site_id)
        try:
            # Would be better to clean all open fds that are not needed, but we don't
            # know the FDs of the result_queue pipe. Can we find it out somehow?
            # Cleanup resources of the apache
            #for x in range(3, 256):
            #    try:
            #        os.close(x)
            #    except OSError, e:
            #        if e.errno == errno.EBADF:
            #            pass
            #        else:
            #            raise

            # Reinitialize logging targets
            log.init_logging()

            if config.site_is_local(site_id):
                automation = AutomationCheckAnalyzeConfig()
                results_data = automation.execute(automation.get_request())

            else:
                results_data = watolib.do_remote_automation(config.site(site_id),
                                                            "check-analyze-config", [])

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
            "user_id": config.user.id,
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
        store.save_data_to_file(self._ack_path, acknowledged_werks)

    def _load_acknowledgements(self, lock=False):
        return store.load_data_from_file(self._ack_path, {}, lock=lock)
