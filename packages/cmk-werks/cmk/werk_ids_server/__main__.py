#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
from pathlib import Path

from flask import Flask
from gunicorn.app.base import BaseApplication

from cmk.werk_ids_server._db import init_db
from cmk.werk_ids_server.server import app

_DB = Path("/var/lib/cmk-werk-ids/werk_ids.db")
_SECRET_FILE = Path("/etc/cmk-werk-ids/secret")
_START = 22_222


class _Server(BaseApplication):
    def load_config(self) -> None:
        assert self.cfg is not None
        self.cfg.set("control_socket_disable", True)
        self.cfg.set("accesslog", "-")  # enable the access log on stdout; off by default

    def load(self) -> Flask:
        return app

    def run(self) -> None:
        super().run()  # type: ignore[no-untyped-call]


parser = argparse.ArgumentParser(description="Werk IDs server")
subparsers = parser.add_subparsers(dest="command", required=True)

subparsers.add_parser("init", help="Initialize the database and exit")
subparsers.add_parser("serve", help="Run the server")

args = parser.parse_args()

# Send the application logs to stderr so they are captured by journald (view with
# 'journalctl -u cmk-werk-ids.service'). gunicorn's forked workers inherit this; its
# own access/error loggers keep their separate handlers.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(process)d] [%(levelname)s] %(name)s: %(message)s",
    datefmt="[%Y-%m-%d %H:%M:%S %z]",
)

if args.command == "init":
    init_db(_DB, _START)
elif args.command == "serve":
    app.config["db"] = _DB
    app.config["secret_file"] = _SECRET_FILE
    init_db(_DB, _START)
    _Server().run()  # type: ignore[no-untyped-call]
else:
    raise AssertionError(f"Unexpected command: {args.command!r}")
