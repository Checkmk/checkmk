#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery import AutochecksStore
from cmk.checkengine.plugins import AutocheckEntry, CheckPlugin, CheckPluginName
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.update_config.plugins.lib.autochecks import get_fixed_autochecks


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    ["existing_autochecks", "expected_autochecks"],
    [
        pytest.param(
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test livestatus proxy",
                    parameters={
                        "process": "~liveproxyd",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                        "cpu_rescale_max": True,
                    },
                    service_labels={},
                ),
            ],
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test livestatus proxy",
                    parameters={
                        "process": "~liveproxyd",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                        "cpu_rescale_max": True,
                    },
                    service_labels={},
                ),
            ],
            id="other ps services discovered",
        ),
        pytest.param(
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test custom name",
                    parameters={
                        "cpu_rescale_max": True,
                        "process": "~gunicorn:.*automation-helper",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                    },
                    service_labels={},
                ),
            ],
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test custom name",
                    parameters={
                        "cpu_rescale_max": True,
                        "process": "~gunicorn:.*automation-helper",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                    },
                    service_labels={},
                ),
            ],
            id="changed item name",
        ),
        pytest.param(
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test automation helpers",
                    parameters={
                        "cpu_rescale_max": True,
                        "process": "~gunicorn:.*automation-helper",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                    },
                    service_labels={},
                ),
            ],
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test automation helpers",
                    parameters={
                        "cpu_rescale_max": True,
                        "process": "~(.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                    },
                    service_labels={},
                ),
            ],
            id="2.4 automation helper process pattern",
        ),
        pytest.param(
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test automation helpers",
                    parameters={
                        "process": "~(.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                        "cpu_rescale_max": True,
                    },
                    service_labels={},
                ),
            ],
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("ps"),
                    item="test automation helpers",
                    parameters={
                        "process": "~(.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
                        "match_groups": (),
                        "user": "test",
                        "cgroup": (None, False),
                        "cpu_rescale_max": True,
                    },
                    service_labels={},
                ),
            ],
            id="already updated 2.5 automation helper process pattern",
        ),
    ],
)
def test_ps_plugin_transforms_automation_helper_pattern(
    existing_autochecks: Sequence[AutocheckEntry], expected_autochecks: Sequence[AutocheckEntry]
) -> None:
    """Test that the old gunicorn automation-helper pattern is transformed to the new pattern."""
    host_name = HostName("test_host")
    AutochecksStore(host_name).write(existing_autochecks)
    rulesets = AllRulesets({})
    check_plugins: dict[CheckPluginName, CheckPlugin] = {}

    generator = get_fixed_autochecks(host_name, rulesets, check_plugins)

    errors = []
    fixed_autochecks = []
    try:
        while True:
            errors.append(next(generator))
    except StopIteration as e:
        fixed_autochecks = e.value

    assert not errors
    assert expected_autochecks == fixed_autochecks
