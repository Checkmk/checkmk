#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Ajax webservice for reschedulung host- and service checks"""

import time
from typing import Any

import livestatus

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId

from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.utils.csrf_token import check_csrf_token


class PageRescheduleCheck(AjaxPage):
    """Is called to trigger a host / service check"""

    def page(self, config: Config) -> PageResult:
        api_request = request.get_request()
        return self._do_reschedule(api_request, config.reschedule_timeout)

    @staticmethod
    def _force_check(now: int, cmd: str, spec: str, site: SiteId) -> None:
        sites.live().command(
            "[%d] SCHEDULE_FORCED_%s_CHECK;%s;%d" % (now, cmd, livestatus.lqencode(spec), now), site
        )

    @staticmethod
    def _wait_for(
        site: SiteId,
        host: str,
        what: str,
        wait_spec: str,
        now: int,
        add_filter: str,
        reschedule_timeout: float,
    ) -> livestatus.LivestatusRow:
        with sites.only_sites(site):
            return sites.live().query_row(
                (
                    "GET %ss\n"
                    "WaitObject: %s\n"
                    "WaitCondition: last_check >= %d\n"
                    "WaitTimeout: %d\n"
                    "WaitTrigger: check\n"
                    "Columns: last_check state plugin_output\n"
                    "Filter: host_name = %s\n%s"
                )
                % (
                    what,
                    livestatus.lqencode(wait_spec),
                    now,
                    reschedule_timeout * 1000,
                    livestatus.lqencode(host),
                    add_filter,
                )
            )

    def _do_reschedule(self, api_request: dict[str, Any], reschedule_timeout: float) -> PageResult:
        if not user.may("action.reschedule"):
            raise MKGeneralException("You are not allowed to reschedule checks.")

        check_csrf_token()

        site = api_request.get("site")
        host = api_request.get("host")
        if not host or not site:
            raise MKGeneralException("Action reschedule: missing host name")

        service = api_request.get("service", "")
        wait_svc = api_request.get("wait_svc", "")

        if service:
            cmd = "SVC"
            what = "service"
            spec = f"{host};{service}"

            if wait_svc:
                wait_spec = f"{host};{wait_svc}"
                add_filter = "Filter: service_description = %s\n" % livestatus.lqencode(wait_svc)
            else:
                wait_spec = spec
                add_filter = "Filter: service_description = %s\n" % livestatus.lqencode(service)
        else:
            cmd = "HOST"
            what = "host"
            spec = host
            wait_spec = spec
            add_filter = ""

        now = int(time.time())

        if service in ("Check_MK Discovery", "Check_MK Inventory"):
            # During discovery, the allowed cache age is (by default) 120 seconds, such that the
            # discovery service won't steal data in the TCP case.
            # But we do want to see new services, so for SNMP we set the cache age to zero.
            # For TCP, we ensure updated caches by triggering the "Check_MK" service whenever the
            # user manually triggers "Check_MK Discovery".
            self._force_check(now, "SVC", f"{host};Check_MK", site)
            self._wait_for(
                site,
                host,
                "service",
                f"{host};Check_MK",
                now,
                "Filter: service_description = Check_MK\n",
                reschedule_timeout,
            )

        self._force_check(now, cmd, spec, site)
        row = self._wait_for(site, host, what, wait_spec, now, add_filter, reschedule_timeout)

        last_check = row[0]
        if last_check < now:
            return {
                "state": "TIMEOUT",
                "message": _("Check not executed within %d seconds") % (reschedule_timeout),
            }

        if service == "Check_MK":
            # Passive services triggered by Checkmk often are updated
            # a few ms later. We introduce a small wait time in order
            # to increase the chance for the passive services already
            # updated also when we return.
            time.sleep(0.7)

        # Row is currently not used by the frontend, but may be useful for debugging
        return {
            "state": "OK",
            "row": row,
        }
