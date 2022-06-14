#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'aws_glacier'


info = [[u'[{"VaultARN":',
         u'"arn:aws:glacier:eu-central-1:710145618630:vaults/axi_empty_vault",',
         u'"VaultName":',
         u'"axi_empty_vault",',
         u'"Label":',
         u'"axi_empty_vault",',
         u'"Values":',
         u'[],',
         u'"NumberOfArchives":',
         u'0,',
         u'"Timestamps":',
         u'[],',
         u'"CreationDate":',
         u'"2019-07-22T09:39:34.135Z",',
         u'"Id":',
         u'"id_0_GlacierMetric",',
         u'"Tagging":',
         u'{},',
         u'"StatusCode":',
         u'"Complete"},',
         u'{"SizeInBytes":',
         u'0,',
         u'"VaultARN":',
         u'"arn:aws:glacier:eu-central-1:710145618630:vaults/axi_vault",',
         u'"VaultName":',
         u'"axi_vault",',
         u'"Label":',
         u'"axi_vault",',
         u'"Values":',
         u'[],',
         u'"Timestamps":',
         u'[],',
         u'"CreationDate":',
         u'"2019-07-18T08:07:01.708Z",',
         u'"Id":',
         u'"id_1_GlacierMetric",',
         u'"Tagging":',
         u'{},',
         u'"StatusCode":',
         u'"Complete"}]']]


discovery = {'': [(u'axi_empty_vault', {}), (u'axi_vault', {})], 'summary': [(None, {})]}


checks = {'': [
                (u'axi_empty_vault',
                {},
                [(0,
                  'Vault size: 0 B',
                  [('aws_glacier_vault_size', 0, None, None, None, None)]),
                 (0,
                  'Number of archives: 0',
                  [('aws_glacier_num_archives', 0, None, None, None, None)])]),

               (u'axi_vault',
                {},
                [(0,
                  'Vault size: 0 B',
                  [('aws_glacier_vault_size', 0, None, None, None, None)]),
                 (0,
                  'Number of archives: 0',
                  [('aws_glacier_num_archives', 0, None, None, None, None)])])
               ],
          'summary': [(None,
                       {},
                       [(0,
                         'Total size: 0 B',
                         [('aws_glacier_total_vault_size',
                           0,
                           None,
                           None,
                           None,
                           None)]),
                        (0,
                         u'Largest vault: axi_vault (0 B)',
                         [('aws_glacier_largest_vault_size',
                           0,
                           None,
                           None,
                           None,
                           None)])])]}
