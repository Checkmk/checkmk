#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import argparse
import logging
import os
import pathlib
import typing

import flask
import werkzeug
from flask import current_app
from werkzeug.exceptions import BadRequest
from werkzeug.security import safe_join
from werkzeug.serving import run_simple

# WARNING:
#   These are selected imports which *do not* pull in other modules from cmk!
# WARNING:
#   In this module, please do not import anything which could, by proxy, import "cmk.utils.paths",
#   because this would "bake in" wrong paths into the module, thus preventing the server from
#   running correctly. This is due to our faked environment variables (see the use of
#   `modified_environ` in this module).
# NOTE:
#   This is not a problem in production, as we have real environment variables there.
from cmk.gui.wsgi.dev_utils import git_absolute, mocked_livestatus, modified_environ

if typing.TYPE_CHECKING:
    from _typeshed.wsgi import WSGIApplication

ResponseTypes = typing.Union[flask.Response, werkzeug.Response]

logger = logging.getLogger(__name__)


def running_in_ide() -> bool:
    # NOTE:
    #   In order to run the server directly from an IDE, spawn it with this environment variable
    #   set, so the reloader is correctly deactivated.
    # RATIONALE:
    #   The reloader detaches the process from the IDE. Because of this, when running in IntelliJ or
    #   PyCharm, the IDE thinks the server has already stopped and exits.
    return os.environ.get("RUNNING_IN_IDE") in ["yes", "1", "t", "true"]


class ColorizingFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s [%(levelname)-8s] [%(name)s] %(message)s (%(filename)s:%(lineno)d)"

    FORMATS: typing.Final[dict[int, str]] = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging() -> None:
    root = logging.getLogger()

    handler = logging.StreamHandler()
    formatter = ColorizingFormatter()
    handler.setFormatter(formatter)

    root.addHandler(handler)


def set_levels(level_name: str, logger_names: list[str]) -> None:
    """Set the logging level of a list of loggers.

    Args:
        level_name:
        logger_names:

    Returns:

    """
    level = getattr(logging, level_name)
    for logger_name in logger_names:
        _logger = logging.getLogger(logger_name)
        _logger.setLevel(level)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.set_defaults(
        environment="development",
        host="localhost",
        port=8080,
        debug=[],
        info=[],
        error=[],
    )
    parser.add_argument(
        "environment",
        metavar="environment",
        nargs="?",
        choices=["development", "testing", "production"],
        help=(
            "The environment in which to run the server. This controls the behavior as follows. "
            "Defaults to %(default)r"
        ),
    )
    parser.add_argument(
        "--host", nargs=1, type=str, help="The hostname to listen on. Defaults to %(default)r"
    )
    parser.add_argument(
        "--port", nargs=1, type=int, help="The port to listen on. Defaults to %(default)s"
    )
    parser.add_argument(
        "--debug", nargs="+", type=str, help="Comma separated logger-names to be set to DEBUG."
    )
    parser.add_argument(
        "--info", nargs="+", type=str, help="Comma separated logger-names to be set to INFO."
    )
    _args = parser.parse_args()
    set_levels("DEBUG", _args.debug)
    set_levels("INFO", _args.info)
    return _args


def prepare_dev_wsgi_app() -> WSGIApplication:
    from cmk.utils import paths

    file_name = paths.htpasswd_file
    if not os.path.exists(file_name):
        logger.warning(os.environ.get("OMD_ROOT"))
        # We're nice and let the developer know.
        logger.warning("%s doesn't exist. No login possible.", file_name)
        logger.warning("Create it using 'htpasswd -B -c %s cmkadmin'", file_name)

    from cmk.gui.wsgi.app import make_wsgi_app

    app = make_wsgi_app(debug=True, testing=False)

    @app.after_request
    def add_header(response: ResponseTypes) -> ResponseTypes:
        # NOTE
        # We don't want to let the browser cache anything, because
        #   that would make it difficult to see our changes.
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.max_age = 0
        return response

    @app.route("/<string:site>/check_mk/themes/<string:theme>/images/<string:file_name>")
    def image_file(site: str, theme: str, file_name: str) -> ResponseTypes:
        icon_path = safe_join(paths.web_dir, "htdocs/themes", theme, "images")
        if icon_path is None:
            raise BadRequest("Unknown path")

        # NOTE
        # "facelift" is the theme which should have all the icons.
        # The other themes aren't expected to have all of them, because any missing icon can be
        # found in "facelift".
        response = flask.send_from_directory(icon_path, file_name)
        if theme != "facelift" and response.status_code == 404:
            return current_app.redirect(
                flask.url_for(
                    "checkmk.image_file",
                    site=site,
                    theme="facelift",
                    file_name=file_name,
                )
            )

        return response

    @app.route("/<string:site>/check_mk/js/<string:file_name>")
    def js_file(site: str, file_name: str) -> flask.Response:
        # Remove cache busters from filename
        main_file_name, rest = file_name.split("-", 1)
        _, ext = rest.rsplit(".", 1)
        return flask.send_from_directory(f"{paths.web_dir}/htdocs/js", f"{main_file_name}.{ext}")

    @app.route("/<string:site>/check_mk/themes/<string:theme>/<string:file_name>")
    def css_file(site: str, theme: str, file_name: str) -> flask.Response:
        main_file_name, rest = file_name.split("-", 1)
        _, ext = rest.rsplit(".", 1)
        path = safe_join(paths.web_dir, "htdocs/themes", theme)
        if path is None:
            raise BadRequest("Unknown path")

        return flask.send_from_directory(path, f"{main_file_name}.{ext}")

    @app.route("/")
    def index() -> ResponseTypes:
        omd_site = os.environ["OMD_SITE"]
        return _redirect_site(omd_site)

    @app.route("/<string:site_name>")
    def site_index(site_name: str) -> ResponseTypes:
        return _redirect_site(site_name)

    def _redirect_site(site_name: str) -> ResponseTypes:
        joined = safe_join(site_name, "check_mk")
        if joined is None:
            raise BadRequest("Unknown path")

        return current_app.redirect(joined)

    return app


def main() -> None:
    setup_logging()
    args = parse_arguments()

    with modified_environ(
        OMD_SITE="dev",
        OMD_ROOT=os.path.expanduser("~/.cmk-sites/dev-2.2"),
    ):
        # IMPORTANT NOTE
        # Any access on any path in the paths module will "bake" the path into the module.
        # No further changes to "OMD_SITE" will have any effect then, thus we need to delay
        # the first access as far as possible, after the environment variable has been set.
        from cmk.utils import paths, store

        paths.web_dir = git_absolute("web")
        paths.local_web_dir = pathlib.Path(git_absolute("web"))
        paths.htpasswd_file = os.path.expanduser("~/.cmk-htpasswd")

        # We need this to be able to automatically create a new user
        store.makedirs(paths.profile_dir)
        store.makedirs(paths.log_dir)

        logger.warning("NOTE: If the design looks like it's missing CSS files, run 'make css'")
        # Note we import and prepare everything within this context manager, because imports will
        # "materialize" with OMD_ROOT baked into it. If we import too soon, we will get wrong paths.
        wsgi_app = prepare_dev_wsgi_app()
        with mocked_livestatus():
            run_simple(
                args.host,
                args.port,
                wsgi_app,
                use_reloader=not running_in_ide(),
            )


if __name__ == "__main__":
    main()
