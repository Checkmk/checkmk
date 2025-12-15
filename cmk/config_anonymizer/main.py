#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import importlib
import logging
import os
import sys
from collections.abc import Sequence
from types import ModuleType

from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui import main_modules as main_modules
from cmk.gui.config import active_config
from cmk.gui.log import init_logging, logger
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.utils.redis import disable_redis


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-t",
        "--target_dirname",
        required=True,
        type=str,
        help="The directory name where the anonymized data is stored ~/var/check_mk/anonymized/{target_dirname}",  # TODO no path traversal
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


class ConfigAnonymizer:
    steps: list[AnonymizeStep]


def _import_optionally(module_name: str, raise_errors: bool) -> ModuleType | None:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if module_name.startswith(str(exc.name)):
            return None  # never choke upon empty/non-existing folders.
        raise  # re-raise exeptions of wrong imports in the module we're importing
    except Exception:
        if raise_errors:
            raise
        return None


def load_plugins(logger: logging.Logger, raise_errors: bool) -> list[AnonymizeStep]:
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
    plugins: dict[str, AnonymizeStep] = {}
    for filename in os.listdir(plugin_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"cmk.config_anonymizer.plugins.{filename[:-3]}"
            module = _import_optionally(module_name, raise_errors=raise_errors)

            for key, value in vars(module).items():
                if key.startswith("anonymize_step") and isinstance(value, AnonymizeStep):
                    plugins[key] = value
    logger.debug(f"Loaded step plugins: {plugins.keys()}")
    return list(plugins.values())


def main(argv: Sequence[str]) -> None:
    args = parse_arguments(argv)
    init_logging()

    try:
        with disable_redis(), gui_context(), SuperUserContext():
            interface = AnonInterface(args.target_dirname, logger)
            plugins = load_plugins(logger, raise_errors=args.debug)
            # TODO: Can we somehow prevent the creation of files outside of the target_dir
            #  e.g. the step is not allowed to create files, just return a list of paths and their content
            logger.debug("Loaded plugins:", [type(p).__name__ for p in plugins])
            for plugin in plugins:
                plugin.run(interface, active_config, logger.getChild("" + type(plugin).__name__))
    except Exception as e:
        logger.exception(f"Error: {e}", exc_info=e)
        raise e from e


if __name__ == "__main__":
    main(sys.argv[1:])
