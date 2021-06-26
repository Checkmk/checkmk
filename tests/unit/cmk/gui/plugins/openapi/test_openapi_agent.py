#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.version as cmk_version


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No agent deployment in raw edition")
def test_deploy_agent(wsgi_app):
    response = wsgi_app.get('/NO_SITE/check_mk/deploy_agent.py')
    assert response.text.startswith("ERROR: Missing or invalid")

    response = wsgi_app.get('/NO_SITE/check_mk/deploy_agent.py?mode=agent')
    assert response.text.startswith("ERROR: Missing host")
