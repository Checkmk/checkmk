#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
import responses
from pytest import MonkeyPatch

from cmk.plugins.salesforce.special_agent.agent_salesforce import main

URL = "https://api.status.salesforce.com/v1/instances/5/status"


def test_wrong_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main()
    assert capsys.readouterr().out == ""


@responses.activate
def test_agent_output(capsys: pytest.CaptureFixture[str], monkeypatch: MonkeyPatch) -> None:
    responses.add(
        responses.GET,
        URL,
        json={"random_answer": "foo-bar"},
        status=200,
    )
    monkeypatch.setattr(
        "sys.argv", ["agent_salesforce", "--section_url", f"salesforce_instances,{URL}"]
    )
    main()
    assert capsys.readouterr() == (
        '<<<salesforce_instances>>>\n{"random_answer": "foo-bar"}\n\n',
        "",
    )
