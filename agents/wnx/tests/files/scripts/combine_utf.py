#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from typing import Final

UTF_16_LE_BOM: Final = b"\xff\xfe"
UTF_8_BOM: Final = b"\xef\xbb\xbf"


def _offset_by_bom(data: bytes) -> int:
    return 2 if data.startswith(UTF_16_LE_BOM) else 3 if data.startswith(UTF_8_BOM) else 0


def read_files(files: list[str]) -> bytes:
    print(f"Processing files: {', '.join(files)}")
    output = b""
    for file in files:
        with open(file, "rb") as f:
            file_data = f.read()
            output += file_data[_offset_by_bom(file_data) :]
    return output


def save_output(file: str, output: bytes) -> None:
    print(f"Saving to file: {file} {len(output)} bytes")
    with open(file, "wb") as f:
        f.write(UTF_16_LE_BOM)
        f.write(output)


def parse_args() -> tuple[str | None, list[str]]:
    parser = argparse.ArgumentParser(
        description="Concatenates files into UTF-16 BOM LE file with dropping BOM marks."
    )
    parser.add_argument("--output", type=str, help="resulting data")
    parser.add_argument(
        "input_files", metavar="file", type=str, nargs="+", help="files with UTF data"
    )
    args = parser.parse_args()

    return args.output, args.input_files


if __name__ == "__main__":
    output_file, input_files = parse_args()
    all_data = read_files(input_files)
    if output_file:
        save_output(output_file, all_data)
    else:
        print(f"Test run: gathered {len(all_data)}")
