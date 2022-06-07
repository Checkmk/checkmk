#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# pylint: disable=no-else-continue


def preparse_emcvnx_info(info):  # pylint: disable=too-many-branches
    def convert(value):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                pass
        return value

    preparsed: list = []
    errors = set()
    skip_lines = 0
    for line in info:
        line = [x.strip() for x in line]
        if len(line) == 1:
            key, value = line[0], None
        else:
            # the value can contain the separator ':'
            key, value = line[0], ":".join(line[1:])

        # fix naviseccli error that does not output a colon for some values
        if value is None and (
            key.startswith("SP Read Cache State") or key.startswith("SP Write Cache State")
        ):
            tmp = key.split()
            key, value = " ".join(tmp[:-1]), tmp[-1]

        error: list[str]
        if key.startswith("Error"):
            skip_lines, error = 1, []
        elif key.startswith("Unable to validate the identity of the server"):
            # assumes that certificate errors are always 10 lines long
            skip_lines, error = 10, []

        if not skip_lines:
            if key.startswith("---"):  # remove headline
                preparsed.pop()
                continue
            elif value is None:  # append in case of a line continuation
                value = key
                old_key, old_value = preparsed[-1]
                preparsed[-1] = (old_key, ", ".join([old_value, value]))
            elif not value:  # remove subheader
                continue
            else:
                preparsed.append((key, convert(value)))
        else:
            error.append(": ".join(line))

            if skip_lines == 1:
                errors.add(" ".join(error))
            skip_lines -= 1

    return preparsed, list(errors)
