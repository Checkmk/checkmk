#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aws_glacier"


info = [
    [
        '[{"VaultARN":',
        '"arn:aws:glacier:eu-central-1:710145618630:vaults/axi_empty_vault",',
        '"VaultName":',
        '"axi_empty_vault",',
        '"Label":',
        '"axi_empty_vault",',
        '"Values":',
        "[],",
        '"NumberOfArchives":',
        "0,",
        '"Timestamps":',
        "[],",
        '"CreationDate":',
        '"2019-07-22T09:39:34.135Z",',
        '"Id":',
        '"id_0_GlacierMetric",',
        '"Tagging":',
        "{},",
        '"StatusCode":',
        '"Complete"},',
        '{"SizeInBytes":',
        "0,",
        '"VaultARN":',
        '"arn:aws:glacier:eu-central-1:710145618630:vaults/axi_vault",',
        '"VaultName":',
        '"axi_vault",',
        '"Label":',
        '"axi_vault",',
        '"Values":',
        "[],",
        '"Timestamps":',
        "[],",
        '"CreationDate":',
        '"2019-07-18T08:07:01.708Z",',
        '"Id":',
        '"id_1_GlacierMetric",',
        '"Tagging":',
        "{},",
        '"StatusCode":',
        '"Complete"}]',
    ]
]


discovery = {"": [("axi_empty_vault", {}), ("axi_vault", {})], "summary": [(None, {})]}


checks = {
    "": [
        (
            "axi_empty_vault",
            {},
            [
                (0, "Vault size: 0 B", [("aws_glacier_vault_size", 0, None, None, None, None)]),
                (
                    0,
                    "Number of archives: 0",
                    [("aws_glacier_num_archives", 0, None, None, None, None)],
                ),
            ],
        ),
        (
            "axi_vault",
            {},
            [
                (0, "Vault size: 0 B", [("aws_glacier_vault_size", 0, None, None, None, None)]),
                (
                    0,
                    "Number of archives: 0",
                    [("aws_glacier_num_archives", 0, None, None, None, None)],
                ),
            ],
        ),
    ],
    "summary": [
        (
            None,
            {},
            [
                (
                    0,
                    "Total size: 0 B",
                    [("aws_glacier_total_vault_size", 0, None, None, None, None)],
                ),
                (
                    0,
                    "Largest vault: axi_vault (0 B)",
                    [("aws_glacier_largest_vault_size", 0, None, None, None, None)],
                ),
            ],
        )
    ],
}
