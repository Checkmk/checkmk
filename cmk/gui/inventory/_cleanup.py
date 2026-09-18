#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.form_specs.generators.age import Age as FSAge
from cmk.gui.form_specs.generators.alternative_utils import enable_deprecated_alternative
from cmk.gui.form_specs.generators.regex_utils import create_regex
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.log import logger
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSiteManagement
from cmk.inventory.cleanup import InventoryCleanup
from cmk.rulesets.internal.form_specs import (
    ListExtended,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    MatchingScope,
    String,
    TimeMagnitude,
    validators,
)


def _fs_text_or_regex() -> TransformDataForLegacyFormatOrRecomposeFunction:
    # Port of the TextOrRegExp() valuespec.
    return enable_deprecated_alternative(
        wrapped_form_spec=CascadingSingleChoice(
            elements=[
                CascadingSingleChoiceElement(
                    name="alternative_explicit",
                    title=Title("Explicit match"),
                    parameter_form=String(title=Title("Explicit match")),
                ),
                CascadingSingleChoiceElement(
                    name="alternative_regex",
                    title=Title("Regular expression match"),
                    parameter_form=TransformDataForLegacyFormatOrRecomposeFunction(
                        wrapped_form_spec=create_regex(
                            MatchingScope.PREFIX,
                            title=Title("Regular expression match"),
                        ),
                        to_disk=lambda value: f"~{value}",
                        from_disk=lambda value: str(value)[1:],
                    ),
                ),
            ],
            prefill=DefaultValue("alternative_explicit"),
        ),
        match_function=lambda value: 1 if value and value[0] == "~" else 0,
    )


def _fs_file_age(title: Title, prefill: int) -> TransformDataForLegacyFormatOrRecomposeFunction:
    return FSAge(
        title=title,
        displayed_magnitudes=[TimeMagnitude.DAY],
        custom_validate=[validators.NumberInRange(min_value=1)],
        prefill=DefaultValue(float(prefill)),
    )


def _fs_file_age_history_entries() -> TransformDataForLegacyFormatOrRecomposeFunction:
    return _fs_file_age(Title("Remove history entries older than"), 400 * 86400)


def _fs_number_of_history_entries() -> Integer:
    return Integer(
        title=Title("Remove history entries right after"),
        label=Label("entry number"),
        prefill=DefaultValue(100),
        custom_validate=[validators.NumberInRange(min_value=1)],
    )


def _fs_choices() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Cleanup parameters"),
        elements=[
            CascadingSingleChoiceElement(
                name="file_age",
                title=Title("Remove history entries older than"),
                parameter_form=_fs_file_age_history_entries(),
            ),
            CascadingSingleChoiceElement(
                name="number_of_history_entries",
                title=Title("Remove history entries right after"),
                parameter_form=_fs_number_of_history_entries(),
            ),
            CascadingSingleChoiceElement(
                name="combined",
                title=Title("Remove history entries which meet the following conditions"),
                parameter_form=Dictionary(
                    title=Title("Use the following defaults"),
                    elements={
                        "strategy": DictElement(
                            required=True,
                            parameter_form=SingleChoiceExtended[str](
                                title=Title("Cleanup strategy"),
                                elements=[
                                    SingleChoiceElementExtended(
                                        name="and",
                                        title=Title("Both conditions must match (defensive)"),
                                    ),
                                    SingleChoiceElementExtended(
                                        name="or",
                                        title=Title("One condition needs to match (offensive)"),
                                    ),
                                ],
                                prefill=DefaultValue("and"),
                            ),
                        ),
                        "file_age": DictElement(
                            required=True,
                            parameter_form=_fs_file_age_history_entries(),
                        ),
                        "number_of_history_entries": DictElement(
                            required=True,
                            parameter_form=_fs_number_of_history_entries(),
                        ),
                    },
                ),
            ),
        ],
        prefill=DefaultValue("file_age"),
    )


ConfigVariableInventoryCleanup = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainGUI,
    ident="inventory_cleanup",
    form_spec=lambda _context: Dictionary(
        title=Title("HW/SW inventory cleanup"),
        elements={
            "for_hosts": DictElement(
                required=True,
                parameter_form=ListExtended(
                    element_template=Dictionary(
                        elements={
                            "regex_or_explicit": DictElement(
                                required=True,
                                parameter_form=ListExtended(
                                    element_template=_fs_text_or_regex(),
                                    title=Title("Match host names"),
                                    custom_validate=[validators.LengthInRange(min_value=1)],
                                    prefill=DefaultValue([]),
                                ),
                            ),
                            "parameters": DictElement(
                                required=True,
                                parameter_form=_fs_choices(),
                            ),
                        },
                    ),
                    title=Title("For specific hosts"),
                    prefill=DefaultValue([]),
                ),
            ),
            "default": DictElement(
                required=True,
                parameter_form=enable_deprecated_alternative(
                    wrapped_form_spec=CascadingSingleChoice(
                        title=Title("Default cleanup parameters"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="alternative_defaults",
                                title=Title("Use the following defaults"),
                                parameter_form=Dictionary(
                                    title=Title("Use the following defaults"),
                                    elements={
                                        "strategy": DictElement(
                                            required=True,
                                            parameter_form=FixedValue(
                                                value="and",
                                                label=Label(
                                                    "Both conditions must match (defensive)"
                                                ),
                                                title=Title("Cleanup strategy"),
                                            ),
                                        ),
                                        "file_age": DictElement(
                                            required=True,
                                            parameter_form=_fs_file_age_history_entries(),
                                        ),
                                        "number_of_history_entries": DictElement(
                                            required=True,
                                            parameter_form=_fs_number_of_history_entries(),
                                        ),
                                    },
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="alternative_no_defaults",
                                title=Title("No defaults"),
                                parameter_form=FixedValue(value=None),
                            ),
                        ],
                        prefill=DefaultValue("alternative_defaults"),
                    )
                ),
            ),
            "abandoned_file_age": DictElement(
                required=True,
                parameter_form=_fs_file_age(
                    Title("Remove abandoned host files older than"), 30 * 86400
                ),
            ),
        },
    ),
)


def _collect_all_raw_host_names(*, is_distributed_setup_remote_site: bool) -> Sequence[str]:
    command = (
        ["check_mk", "--list-hosts", "--include-offline"]
        if is_distributed_setup_remote_site
        else ["check_mk", "--list-hosts", "--all-sites", "--include-offline"]
    )
    try:
        return list(set(subprocess.check_output(command, encoding="utf-8").splitlines()))
    except subprocess.CalledProcessError:
        return []


class InventoryCleanupJob:
    def __init__(self, omd_root: Path) -> None:
        self._cleanup = InventoryCleanup(omd_root)

    def __call__(self, config: Config) -> None:
        self._cleanup.run(
            config.inventory_cleanup,
            host_names=[
                HostName(h)
                for h in _collect_all_raw_host_names(
                    is_distributed_setup_remote_site=is_distributed_setup_remote_site(config.sites)
                )
                if h
            ],
            now=int(time.time()),
            logger=logger,
        )
