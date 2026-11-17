#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.wato.pages.timeperiods import ModeEditTimeperiod
from cmk.gui.watolib.timeperiods import save_timeperiods


@pytest.mark.xfail(strict=True, reason="Crash report 3571: TimePeriodAlreadyExistsError")
@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_saving_a_clone_under_the_cloned_name_is_rejected() -> None:
    save_timeperiods({"office_hours": {"alias": "Office hours", "monday": [("08:00", "17:00")]}})
    request.set_var("clone", "office_hours")
    mode = ModeEditTimeperiod()
    form_value = mode._to_valuespec(mode._timeperiod) | {"alias": "Office hours copy"}

    with pytest.raises(MKUserError) as exc_info:
        mode._valuespec().validate_value(form_value, "timeperiod")

    assert exc_info.value.varname == "timeperiod_p_name"
