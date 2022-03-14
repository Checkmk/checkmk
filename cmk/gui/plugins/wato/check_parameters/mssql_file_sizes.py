#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.utils import mssql_item_spec_instance_tablespace
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Alternative, Dictionary, Filesize, Percentage, Tuple


def _parameter_valuespec_mssql_file_sizes():
    return Dictionary(
        title=_("File Size Levels"),
        elements=[
            (
                "data_files",
                Tuple(
                    title=_("Total data file size: Absolute upper levels"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "log_files",
                Tuple(
                    title=_("Total log file size: Absolute upper levels"),
                    elements=[Filesize(title=_("Warning at")), Filesize(title=_("Critical at"))],
                ),
            ),
            (
                "log_files_used",
                Alternative(
                    title=_("Used log files: Absolute or relative upper levels"),
                    elements=[
                        Tuple(
                            title=_("Upper absolute levels"),
                            elements=[
                                Filesize(title=_("Warning at")),
                                Filesize(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("Upper percentage levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_file_sizes",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_tablespace,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_file_sizes,
        title=lambda: _("MSSQL Log and Data File Sizes"),
    )
)
