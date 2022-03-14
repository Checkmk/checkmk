#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def test_ajax_call(logged_in_wsgi_app):
    ajax_page = "/NO_SITE/check_mk/ajax_popup_move_to_folder.py"
    app = logged_in_wsgi_app
    resp = app.get(
        f"{ajax_page}?ident=test2&what=folder&_ajaxid=1611222306&back_url=wato.py", status=400
    )
    assert "Move this folder to" in resp.text, resp.text
    assert "No WATO folder test2." in resp.text, resp.text

    resp = app.get(f"{ajax_page}?ident=test2&what=folder&back_url=wato.py", status=400)
    assert "Move this folder to" in resp.text, resp.text
    assert "No WATO folder test2." in resp.text, resp.text

    app.get(f"{ajax_page}/{ajax_page}?ident=test2&what=folder&back_url=wato.py", status=404)
