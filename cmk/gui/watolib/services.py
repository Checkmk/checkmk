#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import os
import time
import sys
from hashlib import sha256
from typing import Tuple, List, NamedTuple

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.gui_background_job as gui_background_job

from cmk.gui.i18n import _
from cmk.gui.background_job import BackgroundProcessInterface, JobStatusStates
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob
from cmk.gui.watolib.automations import (
    sync_changes_before_remote_automation,
    check_mk_automation,
)


# Would rather use an Enum for this, but this information is exported to javascript
# using JSON and Enum is not serializable
class DiscoveryAction:
    NONE = ""
    STOP = "stop"
    SCAN = "scan"
    FIX_ALL = "fix_all"
    REFRESH = "refresh"
    SINGLE_UPDATE = "single_update"
    BULK_UPDATE = "bulk_update"
    UPDATE_HOST_LABELS = "update_host_labels"


CheckTableEntry = Tuple  # TODO: Improve this type
CheckTable = List[CheckTableEntry]  # TODO: Improve this type

DiscoveryResult = NamedTuple("DiscoveryResult", [
    ("job_status", dict),
    ("check_table_created", int),
    ("check_table", CheckTable),
    ("host_labels", dict),
])

DiscoveryOptions = NamedTuple("DiscoveryOptions", [
    ("action", str),
    ("show_checkboxes", bool),
    ("show_parameters", bool),
    ("show_discovered_labels", bool),
    ("show_plugin_names", bool),
    ("ignore_errors", bool),
])

StartDiscoveryRequest = NamedTuple("StartDiscoveryRequest", [
    ("host", watolib.CREHost),
    ("folder", watolib.CREFolder),
    ("options", DiscoveryOptions),
])


def checkbox_name(check_type, item):
    """Generate HTML variable for service

    This needs to be unique for each host. Since this text is used as
    variable name, it must not contain any umlauts or other special characters that
    are disallowed by html.parse_field_storage(). Since item may contain such
    chars, we need to use some encoded form of it. Simple escaping/encoding like we
    use for values of variables is not enough here.

    Examples:

        >>> checkbox_name("df", "/opt/omd/sites/testering/tmp")
        '0735e04becbc2f9481ea8e0b54f1aa512d0b04e036cdfac5cc72238f6b39aaeb'

    Returns:
        A string representing the service checkbox

    """
    key = u"%s_%s" % (check_type, item)
    return sha256(key.encode('utf-8')).hexdigest()


def get_check_table(discovery_request):
    # type: (StartDiscoveryRequest) -> DiscoveryResult
    """Gathers the check table using a background job

    Cares about handling local / remote sites using an automation call. In both cases
    the ServiceDiscoveryBackgroundJob is executed to care about collecting the check
    table asynchronously. In case of a remote site the chain is:

    Starting from central site:

    _get_check_table()
          |
          v
    automation service-discovery-job-discover
          |
          v
    to remote site
          |
          v
    AutomationServiceDiscoveryJob().execute()
          |
          v
    _get_check_table()
    """
    if discovery_request.options.action == DiscoveryAction.REFRESH:
        watolib.add_service_change(
            discovery_request.host, "refresh-autochecks",
            _("Refreshed check configuration of host '%s'") % discovery_request.host.name())

    if config.site_is_local(discovery_request.host.site_id()):
        return execute_discovery_job(discovery_request)

    discovery_result = _get_check_table_from_remote(discovery_request)
    discovery_result = _add_missing_service_labels(discovery_result)
    return discovery_result


def execute_discovery_job(request):
    # type: (StartDiscoveryRequest) -> DiscoveryResult
    """Either execute the discovery job to scan the host or return the discovery result
    based on the currently cached data"""
    job = ServiceDiscoveryBackgroundJob(request.host.name())

    if not job.is_active() and request.options.action in [
            DiscoveryAction.SCAN, DiscoveryAction.REFRESH
    ]:
        job.set_function(job.discover, request)
        job.start()

    if job.is_active() and request.options.action == DiscoveryAction.STOP:
        job.stop()

    r = job.get_result(request)
    return r


# 1.6.0b4 introduced the service labels column which might be missing when
# fetching information from remote sites.
def _add_missing_service_labels(discovery_result):
    # type: (DiscoveryResult) -> DiscoveryResult
    d = discovery_result._asdict()
    d["check_table"] = [(e + ({},) if len(e) < 11 else e) for e in d["check_table"]]
    return DiscoveryResult(**d)


def _get_check_table_from_remote(request):
    """Gathers the check table from a remote site

    Cares about pre 1.6 sites that does not support the new service-discovery-job API call.
    Falling back to the previously existing try-inventry and inventory automation calls.
    """
    try:
        sync_changes_before_remote_automation(request.host.site_id())

        return DiscoveryResult(*ast.literal_eval(
            watolib.do_remote_automation(config.site(request.host.site_id()),
                                         "service-discovery-job", [
                                             ("host_name", request.host.name()),
                                             ("options", json.dumps(request.options._asdict())),
                                         ])))
    except watolib.MKAutomationException as e:
        if "Invalid automation command: service-discovery-job" not in "%s" % e:
            raise

        # Compatibility for pre 1.6 remote sites.
        # TODO: Replace with helpful exception in 1.7.
        if request.options.action == DiscoveryAction.REFRESH:
            _counts, _failed_hosts = check_mk_automation(
                request.host.site_id(), "inventory",
                ["@scan", "refresh", request.host.name()])

        if request.options.action == DiscoveryAction.SCAN:
            options = ["@scan"]
        else:
            options = ["@noscan"]

        if not request.options.ignore_errors:
            options.append("@raiseerrors")

        options.append(request.host.name())

        check_table = check_mk_automation(request.host.site_id(), "try-inventory", options)

        return DiscoveryResult(
            job_status={
                "is_active": False,
                "state": JobStatusStates.INITIALIZED,
            },
            check_table=check_table,
            check_table_created=int(time.time()),
            host_labels={},
        )


@gui_background_job.job_registry.register
class ServiceDiscoveryBackgroundJob(WatoBackgroundJob):
    """The background job is always executed on the site where the host is located on"""
    job_prefix = "service_discovery"
    housekeeping_max_age_sec = 86400  # 1 day
    housekeeping_max_count = 20

    @classmethod
    def gui_title(cls):
        return _("Service discovery")

    def __init__(self, host_name):
        # type: (str) -> None
        job_id = "%s-%s" % (self.job_prefix, host_name)
        last_job_status = WatoBackgroundJob(job_id).get_status()

        super(ServiceDiscoveryBackgroundJob, self).__init__(
            job_id,
            title=_("Service discovery"),
            stoppable=True,
            host_name=host_name,
            estimated_duration=last_job_status.get("duration"),
        )

    def discover(self, request, job_interface):
        # type: (StartDiscoveryRequest, BackgroundProcessInterface) -> None
        """Target function of the background job"""
        print("Starting job...")
        if request.options.action == DiscoveryAction.SCAN:
            self._jobstatus.update_status({"title": _("Full scan")})
            self._perform_service_scan(request)

        elif request.options.action == DiscoveryAction.REFRESH:
            self._jobstatus.update_status({"title": _("Automatic refresh")})
            self._perform_automatic_refresh(request)

        else:
            raise NotImplementedError()
        print("Completed.")

    def _perform_service_scan(self, request):
        """The try-inventory automation refreshes the Check_MK internal cache and makes the new
        information available to the next try-inventory call made by get_result()."""
        result = check_mk_automation(request.host.site_id(), "try-inventory",
                                     self._get_automation_options(request))
        sys.stdout.write(result["output"])

    def _perform_automatic_refresh(self, request):
        _counts, _failed_hosts = check_mk_automation(
            request.host.site_id(), "inventory",
            ["@scan", "refresh", request.host.name()])
        # In distributed sites this must not add a change on the remote site. We need to build
        # the way back to the central site and show the information there.
        #count_added, _count_removed, _count_kept, _count_new = counts[request.host.name()]
        #message = _("Refreshed check configuration of host '%s' with %d services") % \
        #            (request.host.name(), count_added)
        #watolib.add_service_change(request.host, "refresh-autochecks", message)

    def _get_automation_options(self, request):
        # type: (StartDiscoveryRequest) -> List[str]
        if request.options.action == DiscoveryAction.SCAN:
            options = ["@scan"]
        else:
            options = ["@noscan"]

        if not request.options.ignore_errors:
            options.append("@raiseerrors")

        options.append(request.host.name())

        return options

    def get_result(self, request):
        # tupe: (StartDiscoveryRequest) -> DiscoveryResult
        """Executed from the outer world to report about the job state"""
        job_status = self.get_status()
        job_status["is_active"] = self.is_active()

        # TODO: Use the correct time. This is difficult because cmk.base does not have a single
        # time for all data of a host. The data sources should be able to provide this information
        # somehow.
        check_table_created = int(time.time())
        result = check_mk_automation(request.host.site_id(), "try-inventory",
                                     ["@noscan", request.host.name()])

        return DiscoveryResult(
            job_status=job_status,
            check_table_created=check_table_created,
            check_table=result["check_table"],
            host_labels=result.get("host_labels", {}),
        )

    def _check_table_file_path(self):
        return os.path.join(self.get_work_dir(), "check_table.mk")
