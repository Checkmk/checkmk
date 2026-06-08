#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""cmk-config-anonymizer

EXPERIMENTAL tool to create anonymized configuration dumps.
"""

import argparse
import importlib
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType

from cmk.base.app import make_app
from cmk.base.config import load, load_all_plugins
from cmk.ccc import store
from cmk.ccc.site import omd_site
from cmk.ccc.version import edition
from cmk.checkengine.plugin_backend import extract_known_discovery_rulesets
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui import main_modules as main_modules
from cmk.gui.config import active_config
from cmk.gui.log import init_logging, logger
from cmk.gui.script_helpers import gui_context
from cmk.gui.session_context import SuperUserContext
from cmk.gui.watolib.rulesets import (
    RulesetCollection,
)
from cmk.gui.watolib.utils import ALL_HOSTS, ALL_SERVICES, NEGATE
from cmk.utils import paths
from cmk.utils.redis import disable_redis


def _validate_target_dirname(value: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError("target_dirname must not be empty")

    dir_path = Path(value)
    if len(dir_path.parts) != 1 or dir_path.parts[0] == "..":
        raise argparse.ArgumentTypeError("target_dirname must be a directory name")

    return value


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, desc = __doc__.split("\n\n")
    parser = argparse.ArgumentParser(prog=prog, description=desc)
    parser.add_argument(
        "-t",
        "--target_dirname",
        required=True,
        type=_validate_target_dirname,
        help="The directory name where the anonymized data is stored ~/var/check_mk/anonymized/{target_dirname}",
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


def _snapshot_mtimes(root: Path, exclude: Path) -> dict[Path, float]:
    snapshot: dict[Path, float] = {}
    if not root.exists():
        return snapshot
    try:
        resolved_exclude: Path | None = exclude.resolve()
    except OSError:
        resolved_exclude = None
    for path in root.rglob("*"):
        try:
            if not path.is_file() or path.is_symlink():
                continue
            if resolved_exclude is not None:
                try:
                    path.resolve().relative_to(resolved_exclude)
                    continue  # inside excluded directory
                except ValueError:
                    pass
            snapshot[path] = path.stat().st_mtime
        except OSError:
            # Files may disappear/be inaccessible during iteration; ignore those.
            continue
    return snapshot


def _warn_about_modifications(
    watched_dirs: Sequence[Path],
    before_by_root: Mapping[Path, Mapping[Path, float]],
    target_dir: Path,
    logger: logging.Logger,
) -> None:
    mtimes_after: dict[Path, dict[Path, float]] = {
        d: _snapshot_mtimes(d, target_dir) for d in watched_dirs
    }

    for root, before in before_by_root.items():
        after = mtimes_after[root]

        added_removed = set(after).symmetric_difference(before)
        logger.warning("Files were added or removed: %s", added_removed)

        modified = sorted(path for path, mtime in after.items() if before.get(path) != mtime)
        for path in modified:
            logger.warning("File modified outside target directory: %s", path)


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
    logger.info(f"Anonymizing configuration to {args.target_dirname}...")

    try:
        main_modules.register(edition(paths.omd_root))

        if errors := main_modules.get_failed_plugins():
            logger.error("The following errors occurred during plug-in loading: %r", errors)
            return

        with disable_redis(), gui_context(), SuperUserContext():
            rule_defaults = store.load_mk_file(
                Path(__file__).parent / "default_rule_values.mk",
                default={
                    "ALL_HOSTS": ALL_HOSTS,
                    "ALL_SERVICES": ALL_SERVICES,
                    "NEGATE": NEGATE,
                    "FOLDER_PATH": "",
                    **RulesetCollection._prepare_empty_rulesets(),
                },
                lock=True,
            )

            all_plugins = load_all_plugins()

            builtin_host_labels_callable = make_app(edition(paths.omd_root)).get_builtin_host_labels
            builtin_host_labels = builtin_host_labels_callable(omd_site())

            loaded_config_result = load(
                discovery_rulesets=extract_known_discovery_rulesets(all_plugins),
                get_builtin_host_labels=builtin_host_labels_callable,
                edition=edition(paths.omd_root),
                with_conf_d=True,
                validate_hosts=False,
            )

            interface = AnonInterface(args.target_dirname, rule_defaults, logger)
            plugins = load_plugins(logger, raise_errors=args.debug)
            logger.debug("Loaded plugins:", [type(p).__name__ for p in plugins])

            watched_dirs = [paths.omd_root / "etc", paths.omd_root / "var/check_mk"]
            mtimes_before: dict[Path, dict[Path, float]] = {
                d: _snapshot_mtimes(d, interface.target_dir) for d in watched_dirs
            }

            for plugin in plugins:
                plugin.run(
                    interface,
                    active_config,
                    loaded_config_result,
                    all_plugins,
                    builtin_host_labels,
                    logger.getChild("" + type(plugin).__name__),
                )

            _warn_about_modifications(watched_dirs, mtimes_before, interface.target_dir, logger)
    except Exception as e:
        logger.exception(f"Error: {e}", exc_info=e)
        raise e from e


# called from bin/cmk-config-anonymizer
if __name__ == "__main__":
    main(sys.argv[1:])
