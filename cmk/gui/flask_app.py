#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

from flask import current_app as current_flask_app
from flask import Flask
from flask.sessions import SessionInterface

from cmk.gui import http
from cmk.gui.features import Features


class CheckmkFlaskApp(Flask):
    request_class = http.Request
    response_class = http.Response

    def __init__(
        self,
        import_name: str,
        session_interface: SessionInterface,
        features: Features,
        static_url_path: str | None = None,
        static_folder: str | os.PathLike[str] | None = "static",
        static_host: str | None = None,
        host_matching: bool = False,
        subdomain_matching: bool = False,
        template_folder: str | os.PathLike[str] | None = "templates",
        instance_path: str | None = None,
        instance_relative_config: bool = False,
        root_path: str | None = None,
    ):
        super().__init__(
            import_name,
            static_url_path,
            static_folder,
            static_host,
            host_matching,
            subdomain_matching,
            template_folder,
            instance_path,
            instance_relative_config,
            root_path,
        )
        self.session_interface = session_interface
        self.features = features


def current_app() -> CheckmkFlaskApp:
    app = current_flask_app
    assert isinstance(app, CheckmkFlaskApp)
    return app
