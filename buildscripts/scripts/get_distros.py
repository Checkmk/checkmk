#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import ArgumentParser
from argparse import Namespace as Args
from collections.abc import Iterable

import yaml


def print_internal_build_artifacts(args: Args, loaded_yaml: dict) -> None:
    distros = flatten(loaded_yaml["internal_distros"])
    editions = flatten(loaded_yaml["internal_editions"])

    if args.as_codename:
        if diff := distros - loaded_yaml["distro_to_codename"].keys():
            raise Exception(
                f"{args.editions_file} is missing the distro code for the following distros: "
                f"{diff}. Please add the corresponding distro code."
            )
        distros = [loaded_yaml["distro_to_codename"][d] for d in distros]
    if args.as_rsync_exclude_pattern:
        print("{" + ",".join([f"'*{d}*'" for d in list(distros) + list(editions)]) + "}")
        return

    print(" ".join(sorted(set(distros).union(set(editions)))))


def distros_for_use_case(edition_distros: dict, edition: str, use_case: str) -> Iterable[str]:
    return sorted(
        set(
            distro
            for _edition, use_cases in edition_distros.items()
            if _edition == edition
            for _use_case, distros in use_cases.items()
            if _use_case == use_case
            for distro in flatten(distros)
        )
    )


def print_distros_for_use_case(args: Args, loaded_yaml: dict) -> None:
    edition_distros = loaded_yaml["editions"]
    edition = args.edition
    use_case = args.use_case
    print(" ".join(distros_for_use_case(edition_distros, edition, use_case)))


def print_editions(args: Args, loaded_yaml: dict) -> None:
    print(" ".join(sorted(loaded_yaml["editions"].keys())))


def flatten(list_to_flatten: Iterable[Iterable[str] | str]) -> Iterable[str]:
    # This is a workaround the fact that yaml cannot "extend" a predefined node which is a list:
    # https://stackoverflow.com/questions/19502522/extend-an-array-in-yaml
    return [h for elem in list_to_flatten for h in ([elem] if isinstance(elem, str) else elem)]


def test_distro_lists():
    with open(Path(__file__).parent.parent.parent / "editions.yml") as editions_file:
        edition_distros = yaml.load(editions_file, Loader=yaml.FullLoader)["editions"]
    assert distros_for_use_case(edition_distros, "enterprise", "release") == [
        "almalinux-9",
        "centos-8",
        "cma-3",
        "cma-4",
        "debian-10",
        "debian-11",
        "debian-12",
        "sles-12sp5",
        "sles-15sp3",
        "sles-15sp4",
        "sles-15sp5",
        "ubuntu-20.04",
        "ubuntu-22.04",
        "ubuntu-24.04",
    ]
    assert distros_for_use_case(edition_distros, "enterprise", "daily") == [
        "almalinux-9",
        "centos-8",
        "cma-3",
        "cma-4",
        "debian-10",
        "debian-11",
        "debian-12",
        "sles-12sp5",
        "sles-15sp3",
        "sles-15sp4",
        "sles-15sp5",
        "ubuntu-20.04",
        "ubuntu-22.04",
        "ubuntu-23.10",
        "ubuntu-24.04",
    ]


def parse_arguments() -> Args:
    parser = ArgumentParser()

    parser.add_argument("--editions_file", required=True)

    subparsers = parser.add_subparsers(required=True, dest="command")

    all_distros_subparser = subparsers.add_parser(
        "all", help="Print distros for all use case and all distros"
    )
    all_distros_subparser.set_defaults(func=print_distros_for_use_case)
    all_distros_subparser.add_argument("--edition", default="all")
    all_distros_subparser.add_argument("--use_case", default="all")

    use_cases_subparser = subparsers.add_parser("use_cases", help="Print distros for use case")
    use_cases_subparser.set_defaults(func=print_distros_for_use_case)
    use_cases_subparser.add_argument("--edition", required=True)
    use_cases_subparser.add_argument("--use_case", required=True)

    editions_subparser = subparsers.add_parser("editions", help="Print all supported edtions")
    editions_subparser.set_defaults(func=print_editions)

    internal_build_artifacts = subparsers.add_parser("internal_build_artifacts")
    internal_build_artifacts.set_defaults(func=print_internal_build_artifacts)
    internal_build_artifacts.add_argument("--as-codename", default=False, action="store_true")
    internal_build_artifacts.add_argument(
        "--as-rsync-exclude-pattern", default=False, action="store_true"
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    with open(args.editions_file) as editions_file:
        args.func(args, yaml.load(editions_file, Loader=yaml.FullLoader))


if __name__ == "__main__":
    main()
