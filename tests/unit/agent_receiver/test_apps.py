#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from agent_receiver.apps import agent_receiver_app, main_app
from starlette.routing import Mount


def test_main_app_structure() -> None:
    main_app_ = main_app()
    # we only want one route, namely the one to the sub-app which is mounted under the site name
    assert len(main_app_.routes) == 1
    assert isinstance(mount := main_app_.routes[0], Mount)
    assert mount.app is agent_receiver_app
