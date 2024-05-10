#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "aws_glacier"


info = [
    [
        '[{"SizeInBytes":',
        "0,",
        '"VaultARN":',
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
        "22548578304,",
        '"VaultARN":',
        '"arn:aws:glacier:eu-central-1:710145618630:vaults/fake_vault_1",',
        '"VaultName":',
        '"fake_vault_1",',
        '"Label":',
        '"fake_vault_1",',
        '"Values":',
        "[],",
        '"NumberOfArchives":',
        "2025,",
        '"Timestamps":',
        "[],",
        '"CreationDate":',
        '"2019-07-18T08:07:01.708Z",',
        '"Id":',
        '"id_2_GlacierMetric",',
        '"Tagging":',
        "{},",
        '"StatusCode":',
        '"Complete"},',
        '{"SizeInBytes":',
        "117440512,",
        '"VaultARN":',
        '"arn:aws:glacier:eu-central-1:710145618630:vaults/fake_vault_2",',
        '"VaultName":',
        '"fake_vault_2",',
        '"Label":',
        '"fake_vault_2",',
        '"Values":',
        "[],",
        '"NumberOfArchives":',
        "17,",
        '"Timestamps":',
        "[],",
        '"CreationDate":',
        '"2019-07-18T08:07:01.708Z",',
        '"Id":',
        '"id_3_GlacierMetric",',
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
        '"NumberOfArchives":',
        "0,",
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


discovery = {
    "": [("axi_empty_vault", {}), ("axi_vault", {}), ("fake_vault_1", {}), ("fake_vault_2", {})],
    "summary": [(None, {})],
}


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
        (
            "fake_vault_1",
            {},
            [
                (
                    0,
                    "Vault size: 22.5 GB",
                    [("aws_glacier_vault_size", 22548578304, None, None, None, None)],
                ),
                (
                    0,
                    "Number of archives: 2025",
                    [("aws_glacier_num_archives", 2025, None, None, None, None)],
                ),
            ],
        ),
        (
            "fake_vault_2",
            {},
            [
                (
                    0,
                    "Vault size: 117 MB",
                    [("aws_glacier_vault_size", 117440512, None, None, None, None)],
                ),
                (
                    0,
                    "Number of archives: 17",
                    [("aws_glacier_num_archives", 17, None, None, None, None)],
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
                    "Total size: 22.7 GB",
                    [("aws_glacier_total_vault_size", 22666018816, None, None, None, None)],
                ),
                (
                    0,
                    "Largest vault: fake_vault_1 (22.5 GB)",
                    [("aws_glacier_largest_vault_size", 22548578304, None, None, None, None)],
                ),
            ],
        )
    ],
}
