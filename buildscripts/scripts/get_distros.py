#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse

import yaml


def flatten_list(list_to_flatten: list[list[str] | str]) -> list[str]:
    # This is a workaround the fact that yaml cannot "extend" a predefined node which is a list:
    # https://stackoverflow.com/questions/19502522/extend-an-array-in-yaml
    return [h for elem in list_to_flatten for h in (elem if isinstance(elem, list) else [elem])]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--edition", required=True)
    parser.add_argument("--editions_file", required=True)
    parser.add_argument("--use_case", required=True)
    return parser.parse_args()


args = parse_arguments()
yaml_loaded = yaml.load(open(args.editions_file), Loader=yaml.FullLoader)

print(" ".join(flatten_list(yaml_loaded["editions"][args.edition][args.use_case])))
