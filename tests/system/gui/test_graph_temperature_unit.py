#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The user's temperature unit reaches the rendered graph.

The axis unit comes from the page shell and the legend's from the fetch response - two
separate backend paths, so reading only one would not catch them disagreeing.
"""

import time
import uuid
from collections.abc import Iterator
from typing import Final

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.api_helpers import LOCALHOST_IPV4
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import ServiceGraphs
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.service import ServicePage
from tests.system.gui.testlib.playwright.pom.monitor.services_of_host import ServicesOfHostPage
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.site import ADMIN_USER, Site

# Its plug-in unit is degrees Celsius, so this is the metric the profile setting re-renders.
_TEMPERATURE_METRIC: Final = "temp"

_DEGREE_CELSIUS: Final = "°C"
_DEGREE_FAHRENHEIT: Final = "°F"

# One thermal zone, which `lnx_thermal` discovers as a service carrying `temp`.
_THERMAL_AGENT_DUMP: Final = """<<<check_mk>>>
Version: 2.4.0
AgentOS: linux

<<<lnx_thermal>>>
thermal_zone0 enabled acpitz 57000 127000 critical
"""


@pytest.fixture(name="fahrenheit_profile")
def fixture_fahrenheit_profile(test_site: Site) -> Iterator[None]:
    """`ADMIN_USER` on Fahrenheit - the browser's user, not the one the REST client acts as."""

    def set_unit(unit: str) -> None:
        user = test_site.openapi.users.get(ADMIN_USER)
        assert user is not None, f"The site has no {ADMIN_USER} to set the preference on"
        _user_spec, etag = user
        test_site.openapi.users.edit(ADMIN_USER, {"temperature_unit": unit}, etag)

    set_unit("fahrenheit")
    stored = test_site.openapi.users.get(ADMIN_USER)
    kept = stored[0].get("temperature_unit") if stored else None
    assert kept == "fahrenheit", f"The profile did not keep the Fahrenheit setting: {kept!r}"
    try:
        yield
    finally:
        set_unit("default")


@pytest.fixture(name="temperature_service", scope="module")
def fixture_temperature_service(test_site: Site) -> Iterator[tuple[str, str]]:
    """A monitored host whose only service is a Celsius temperature.

    The site's own agent dumps carry none, so a datasource program feeds one throwaway host.
    """
    host_name = f"temp-graph-{uuid.uuid4().hex[:8]}"
    dumps_path = test_site.path("var/check_mk/dumps")
    rule_id: str | None = None
    try:
        if not test_site.is_dir(dumps_path):
            test_site.makedirs(dumps_path)
        test_site.write_file(f"var/check_mk/dumps/{host_name}", _THERMAL_AGENT_DUMP)
        rule_id = test_site.openapi.rules.create(
            ruleset_name="datasource_programs",
            value=f'cat "{dumps_path.as_posix()}/$HOSTNAME$"',
        )
        test_site.openapi.hosts.create(
            host_name,
            attributes={"ipaddress": LOCALHOST_IPV4, "tag_agent": "cmk-agent"},
        )
        test_site.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion([host_name])
        test_site.openapi.changes.activate_and_wait_for_completion()
        test_site.reschedule_services(host_name)

        rows = test_site.live.query(
            f"GET services\nColumns: description\n"
            f"Filter: host_name = {host_name}\n"
            f"Filter: metrics >= {_TEMPERATURE_METRIC}\n"
        )
        assert rows, f"Host {host_name!r} discovered no service carrying {_TEMPERATURE_METRIC!r}"
        service_name = str(rows[0][0])

        # Without a sample the axis auto-scales to a bare 0..1 and the legend renders no values.
        def _has_samples() -> bool:
            window = int(time.time())
            # An rrddata column comes back as [start, end, step, *values].
            data = test_site.live.query_value(
                f"GET services\n"
                f"Columns: rrddata:{_TEMPERATURE_METRIC}:{_TEMPERATURE_METRIC}.max:"
                f"{window - 3600}:{window}:60\n"
                f"Filter: host_name = {host_name}\n"
                f"Filter: description = {service_name}\n"
            )
            if any(value is not None for value in data[3:]):
                return True
            # rrdcached buffers writes, so one check may not be visible yet; keep nudging.
            test_site.schedule_check(host_name, "Check_MK", 0)
            return False

        wait_until(
            _has_samples,
            timeout=300,
            interval=10,
            condition_name=f"RRD of {host_name}/{service_name} holds a sample",
        )
        yield host_name, service_name
    finally:
        if is_cleanup_enabled():
            test_site.openapi.hosts.bulk_delete([host_name], ignore_missing=True)
            if rule_id is not None:
                test_site.openapi.rules.delete(rule_id)
            test_site.delete_file(f"var/check_mk/dumps/{host_name}")
            test_site.openapi.changes.activate_and_wait_for_completion()


def _open_graphs(dashboard_page: MainDashboard, host_name: str, service_name: str) -> ServiceGraphs:
    page = dashboard_page.page
    services_of_host = ServicesOfHostPage(page, host_name=host_name)
    services_of_host.services_table.host_services_table(host_name).get_by_role(
        "link", name=service_name, exact=True
    ).click()
    graphs = ServiceGraphs(
        ServicePage(page, host_name=host_name, service_name=service_name, navigate_to_page=False)
    )
    graphs.wait_until_rendered()
    graphs.wait_until_settled()
    return graphs


@pytest.mark.usefixtures("fahrenheit_profile")
def test_a_fahrenheit_profile_reaches_the_axis_and_the_legend(
    dashboard_page: MainDashboard,
    temperature_service: tuple[str, str],
    javascript_errors: list[str],
) -> None:
    host_name, service_name = temperature_service

    panel = _open_graphs(dashboard_page, host_name, service_name).panel(0)

    axis_labels = [label for label, _offset in panel.graph.value_axis_ticks()]
    assert axis_labels, "The graph drew no value-axis ticks to read a unit off"
    # The zero tick is drawn bare, so assert by presence and by absence rather than on every label.
    assert any(_DEGREE_FAHRENHEIT in label for label in axis_labels), (
        f"The value axis did not follow the profile's Fahrenheit setting: {axis_labels}"
    )
    assert not any(_DEGREE_CELSIUS in label for label in axis_labels), (
        f"The value axis still carries the metric's own Celsius unit: {axis_labels}"
    )

    # The warn/crit rows are served as horizontal lines of their own, so the legend is the half
    # most likely to be left behind in the metric's own unit.
    expect(
        panel.legend, "The legend did not follow the profile's Fahrenheit setting"
    ).to_contain_text(_DEGREE_FAHRENHEIT)
    expect(
        panel.legend, "The legend still carries Celsius values alongside the Fahrenheit ones"
    ).not_to_contain_text(_DEGREE_CELSIUS)

    assert not javascript_errors, f"The graph raised errors while rendering: {javascript_errors}"
