#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.update_config.plugins.lib.autochecks import _transform_automation_helper_ps_patterns


def test_transform_rewrites_24_gunicorn_pattern() -> None:
    assert _transform_automation_helper_ps_patterns(
        "mysite automation helpers",
        {
            "process": "~gunicorn:.*automation-helper",
            "match_groups": (),
            "user": None,
            "cgroup": (None, False),
            "cpu_rescale_max": True,
        },
    ) == {
        "process": "~(?:.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
        "match_groups": (),
        "user": None,
        "cgroup": (None, False),
        "cpu_rescale_max": True,
    }


def test_transform_drops_stale_match_groups_of_capturing_pattern() -> None:
    assert _transform_automation_helper_ps_patterns(
        "mysite automation helpers",
        {
            "process": "~(.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
            "match_groups": ("gunicorn: worker [automation-helper]",),
            "user": None,
            "cgroup": (None, False),
            "cpu_rescale_max": True,
        },
    ) == {
        "process": "~(?:.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
        "match_groups": (),
        "user": None,
        "cgroup": (None, False),
        "cpu_rescale_max": True,
    }


def test_transform_keeps_current_pattern() -> None:
    assert _transform_automation_helper_ps_patterns(
        "mysite automation helpers",
        {
            "process": "~(?:.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
            "match_groups": (),
            "user": None,
            "cgroup": (None, False),
            "cpu_rescale_max": True,
        },
    ) == {
        "process": "~(?:.*cmk-automation-helper.*|gunicorn:.*automation-helper)",
        "match_groups": (),
        "user": None,
        "cgroup": (None, False),
        "cpu_rescale_max": True,
    }


def test_transform_keeps_other_ps_services() -> None:
    assert _transform_automation_helper_ps_patterns(
        "my own gunicorn service",
        {
            "process": "~gunicorn:.*automation-helper",
            "match_groups": (),
            "user": None,
            "cgroup": (None, False),
            "cpu_rescale_max": True,
        },
    ) == {
        "process": "~gunicorn:.*automation-helper",
        "match_groups": (),
        "user": None,
        "cgroup": (None, False),
        "cpu_rescale_max": True,
    }
