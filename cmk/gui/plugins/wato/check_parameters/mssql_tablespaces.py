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


def _parameter_valuespec_mssql_tablespaces():
    return Dictionary(
        elements=[
            (
                "size",
                Tuple(
                    title=_("Upper levels for size"),
                    elements=[Filesize(title=_("Warning at")), Filesize(title=_("Critical at"))],
                ),
            ),
            (
                "reserved",
                Alternative(
                    title=_("Upper levels for reserved space"),
                    elements=[
                        Tuple(
                            title=_("Absolute levels"),
                            elements=[
                                Filesize(title=_("Warning at")),
                                Filesize(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("Percentage levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "data",
                Alternative(
                    title=_("Upper levels for data"),
                    elements=[
                        Tuple(
                            title=_("Absolute levels"),
                            elements=[
                                Filesize(title=_("Warning at")),
                                Filesize(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("Percentage levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "indexes",
                Alternative(
                    title=_("Upper levels for indexes"),
                    elements=[
                        Tuple(
                            title=_("Absolute levels"),
                            elements=[
                                Filesize(title=_("Warning at")),
                                Filesize(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("Percentage levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "unused",
                Alternative(
                    title=_("Upper levels for unused space"),
                    elements=[
                        Tuple(
                            title=_("Absolute levels"),
                            elements=[
                                Filesize(title=_("Warning at")),
                                Filesize(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("Percentage levels"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                    ],
                ),
            ),
            (
                "unallocated",
                Alternative(
                    title=_("Lower levels for unallocated space"),
                    elements=[
                        Tuple(
                            title=_("Absolute levels"),
                            elements=[
                                Filesize(title=_("Warning below")),
                                Filesize(title=_("Critical below")),
                            ],
                        ),
                        Tuple(
                            title=_("Percentage levels"),
                            elements=[
                                Percentage(title=_("Warning below")),
                                Percentage(title=_("Critical below")),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_tablespaces",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_tablespace,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_tablespaces,
        title=lambda: _("MSSQL Size of Tablespace"),
    )
)
