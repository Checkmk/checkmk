#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--id", required=True)
args = parser.parse_args()

print("<<<multicalltest>>>")
print(f"called_with={args.id}")
