#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
import responses  # type: ignore[import]

from cmk.special_agents.agent_salesforce import main

URL = "https://api.status.salesforce.com/v1/instances/5/status"


def test_wrong_arguments(capsys):
    with pytest.raises(SystemExit):
        main()
    assert capsys.readouterr().out == ""


@responses.activate
def test_agent_output(capsys, monkeypatch):
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
