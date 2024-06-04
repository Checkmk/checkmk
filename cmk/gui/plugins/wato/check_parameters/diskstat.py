#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Final

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Age, Dictionary, DropdownChoice, FixedValue, TextInput, Transform

from .transforms import scale_levels


def migrate_physical(value: dict[str, Any]) -> dict[str, bool | str]:
    if "physical" not in value:
        return value

    return {
        **value,
        "physical": value["physical"] if value["physical"] in ("wwn", "name") else "name",
    }


def _valuespec_diskstat_inventory() -> Transform:
    return Transform(
        Dictionary(
            title=_("Disk IO discovery"),
            help=_(
                "This rule controls which and how many checks will be created "
                "for monitoring individual physical and logical disks. "
                "Note: the option <i>Create a summary for all read, one for "
                "write</i> has been removed. Some checks will still support "
                "this settings, but it will be removed there soon."
            ),
            elements=[
                (
                    "summary",
                    FixedValue(
                        value=True,
                        title=_("Summary"),
                        totext="Create a summary over all physical disks",
                    ),
                ),
                (
                    "physical",
                    DropdownChoice(
                        title=_("Physical disks"),
                        choices=[
                            ("wwn", _("Use World Wide Name (WWN) as service description")),
                            ("name", _("Use device name as service description")),
                        ],
                        default_value="wwn",
                        help=_(
                            "Using device name as service description isn't recommended. "
                            "Device names aren't persistent and can change after a reboot or an update. "
                            "In case WWN is not available, device name will be used."
                        ),
                    ),
                ),
                (
                    "lvm",
                    FixedValue(
                        value=True,
                        title=_("LVM volumes (Linux)"),
                        totext="Create a separate check for each LVM volume (Linux)",
                    ),
                ),
                (
                    "vxvm",
                    FixedValue(
                        value=True,
                        title=_("VxVM volumes (Linux)"),
                        totext="Create a separate check for each VxVM volume (Linux)",
                    ),
                ),
                (
                    "diskless",
                    FixedValue(
                        value=True,
                        title=_("Partitions (XEN)"),
                        totext="Create a separate check for each partition (XEN)",
                    ),
                ),
            ],
            default_keys=["summary"],
        ),
        forth=migrate_physical,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        name="diskstat_inventory",
        valuespec=_valuespec_diskstat_inventory,
    )
)


def _item_spec_diskstat():
    return TextInput(
        title=_("Device"),
        help=_(
            "For a summarized throughput of all disks, specify <tt>SUMMARY</tt>,  "
            "a per-disk IO is specified by the drive letter, a colon and a slash on Windows "
            "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>)."
        ),
    )


_KEY_MAP: Final = {
    "read": "read_throughput",
    "write": "write_throughput",
    "read_wait": "average_read_wait",
    "write_wait": "average_write_wait",
}


_SCALES: Final = {
    "read_throughput": 1e6,
    "write_throughput": 1e6,
    "utilization": 0.01,
    "latency": 1e-3,
    "read_latency": 1e-3,
    "write_latency": 1e-3,
    "average_wait": 1e-3,
    "average_read_wait": 1e-3,
    "average_write_wait": 1e-3,
}

_NEEDS_CONVERSION = "_NEEDS_CONVERSION"


def scale_forth(p: dict[str, Any]) -> dict[str, Any]:
    """If this is seconds and bytes (good), convert into something more readable

    >>> scale_forth({"read_wait": (23.0, 42.0)})
    {'average_read_wait': (23.0, 42.0)}
    >>> scale_forth({"_NEEDS_CONVERSION": True, "latency": (0.023, 0.042)})
    {'latency': (23.0, 42.0)}
    """
    if _NEEDS_CONVERSION not in p:
        # first time, "back" has not ever been called
        return {_KEY_MAP.get(k, k): v for k, v in p.items()}
    return {
        k: scale_levels(v, 1.0 / _SCALES[k]) if k in _SCALES else v
        for k, v in p.items()
        if k != _NEEDS_CONVERSION
    }


def scale_back(p: dict[str, Any]) -> dict[str, Any]:
    """Store the nicely rendered ms or MB values in seconds or bytes

    >>> scale_back({"latency": (23.0, 42.0)})
    {'latency': (0.023, 0.042), '_NEEDS_CONVERSION': True}
    """
    return {
        **{k: scale_levels(v, _SCALES[k]) if k in _SCALES else v for k, v in p.items()},
        _NEEDS_CONVERSION: True,
    }


def _parameter_valuespec_diskstat():
    return Transform(
        Dictionary(
            help=_(
                "With this rule you can set limits for various disk IO statistics. "
                "Keep in mind that not all of these settings may be applicable for the actual "
                "check. For example, if the check doesn't provide a <i>Read wait</i> information in its "
                "output, any configuration setting referring to <i>Read wait</i> will have no effect."
            ),
            elements=[
                (
                    "read_throughput",
                    Levels(
                        title=_("Read throughput"),
                        unit=_("MB/s"),
                        default_levels=(50.0, 100.0),
                    ),
                ),
                (
                    "write_throughput",
                    Levels(
                        title=_("Write throughput"),
                        unit=_("MB/s"),
                        default_levels=(50.0, 100.0),
                    ),
                ),
                (
                    "utilization",
                    Levels(
                        title=_("Disk Utilization"),
                        unit=_("%"),
                        default_levels=(80.0, 90.0),
                    ),
                ),
                (
                    "latency",
                    Levels(
                        title=_("Disk Latency"),
                        unit=_("ms"),
                        default_levels=(80.0, 160.0),
                    ),
                ),
                (
                    "read_latency",
                    Levels(
                        title=_("Disk Read Latency"),
                        unit=_("ms"),
                        default_levels=(80.0, 160.0),
                    ),
                ),
                (
                    "write_latency",
                    Levels(
                        title=_("Disk Write Latency"),
                        unit=_("ms"),
                        default_levels=(80.0, 160.0),
                    ),
                ),
                (
                    "average_read_wait",
                    Levels(title=_("Read wait"), unit=_("ms"), default_levels=(30.0, 50.0)),
                ),
                (
                    "average_write_wait",
                    Levels(title=_("Write wait"), unit=_("ms"), default_levels=(30.0, 50.0)),
                ),
                (
                    "average",
                    Age(
                        title=_("Averaging"),
                        help=_(
                            "When averaging is set, then all of the disk's metrics are averaged "
                            "over the selected interval - rather then the check interval. This allows "
                            "you to make your monitoring less reactive to short peaks. But it will also "
                            "introduce a loss of accuracy in your graphs. "
                        ),
                        default_value=300,
                    ),
                ),
                (
                    "read_ios",
                    Levels(
                        title=_("Read operations"), unit=_("1/s"), default_levels=(400.0, 600.0)
                    ),
                ),
                (
                    "write_ios",
                    Levels(
                        title=_("Write operations"), unit=_("1/s"), default_levels=(300.0, 400.0)
                    ),
                ),
            ],
        ),
        forth=scale_forth,
        back=scale_back,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="diskstat",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_diskstat,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_diskstat,
        title=lambda: _("Disk IO levels"),
    )
)
