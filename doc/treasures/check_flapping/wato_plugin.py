#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is the WATO plugin to configure the active check check_flapping
# via WATO. This plugin must be placed in web/plugins/wato directory.

register_rule("activechecks",
              "active_checks:flapping",
              Tuple(title=_("Check Flapping Services"),
                    help=_("Checks wether or not one or several services changed their states "
                           "too often in the given timeperiod."),
                    elements=[
                        TextInput(title=_("Name"),
                                    help=_("Will be used in the service description"),
                                    allow_empty=False),
                        ListOfStrings(
                            title=_("Patterns to match services"),
                            orientation="horizontal",
                            valuespec=RegExp(size=30),
                        ),
                        Dictionary(title=_("Optional parameters"),
                                   elements=[("num_state_changes",
                                              Tuple(title=_("State change thresholds"),
                                                    elements=[
                                                        Integer(title=_("Warning at"),
                                                                default_value=2),
                                                        Integer(title=_("Critical at"),
                                                                default_value=3),
                                                    ])),
                                             (
                                                 "timerange",
                                                 Integer(title=_("Timerange to check"),
                                                         unit=_('Minutes'),
                                                         default_value=60),
                                             )])
                    ]),
              match='all')
