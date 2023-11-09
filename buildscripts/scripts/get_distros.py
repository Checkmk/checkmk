#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
from collections.abc import Callable, Mapping

import yaml


def print_internal_distros(arguments: argparse.Namespace, loaded_yaml: dict) -> None:
    distros = flatten_list(loaded_yaml["internal_distros"])
    if arguments.as_codename:
        if diff := distros - loaded_yaml["distro_to_codename"].keys():
            raise Exception(
                f"{args.editions_file} is missing the distro code for the following distros: "
                f"{diff}. Please add the corresponding distro code."
            )
        distros = [loaded_yaml["distro_to_codename"][d] for d in distros]
    if arguments.as_rsync_exclude_pattern:
        print("{" + ",".join([f"'*{d}*'" for d in distros]) + "}")
        return

    print(" ".join(distros))


def print_distros_for_use_case(arguments: argparse.Namespace, loaded_yaml: dict) -> None:
    print(" ".join(flatten_list(loaded_yaml["editions"][arguments.edition][arguments.use_case])))


COMMANDS_TO_FUNCTION: Mapping[str, Callable[[argparse.Namespace, dict], None]] = {
    "internal_distros": print_internal_distros,
    "use_cases": print_distros_for_use_case,
}


def flatten_list(list_to_flatten: list[list[str] | str]) -> list[str]:
    # This is a workaround the fact that yaml cannot "extend" a predefined node which is a list:
    # https://stackoverflow.com/questions/19502522/extend-an-array-in-yaml
    return [h for elem in list_to_flatten for h in (elem if isinstance(elem, list) else [elem])]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--editions_file", required=True)
    subparsers = parser.add_subparsers(required=True, dest="command")
    use_cases = subparsers.add_parser("use_cases", help="a help")
    use_cases.add_argument("--edition", required=True)
    use_cases.add_argument("--use_case", required=True)

    internal_distros = subparsers.add_parser("internal_distros")
    internal_distros.add_argument("--as-codename", default=False, action="store_true")
    internal_distros.add_argument("--as-rsync-exclude-pattern", default=False, action="store_true")

    return parser.parse_args()


args = parse_arguments()
with open(args.editions_file) as editions_file:
    COMMANDS_TO_FUNCTION[args.command](args, yaml.load(editions_file, Loader=yaml.FullLoader))
