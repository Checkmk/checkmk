<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'

import CmkDonutChart, { type DonutSlice } from '@/dashboard/components/CmkDonutChart'

const bytes = new SIFormatter('B', { type: 'strict', digits: 2 })
const formatBytes = (value: number): string => bytes.render(value)

const slices: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 4_720_000_000, color: 'blue' },
  { key: 'pops', label: 'POPS', value: 1_700_000_000, color: 'purple' },
  // The remainder is the one slice with a breakdown behind it.
  { key: 'other', label: 'Other', value: 3_580_000_000, color: 'grey', isOther: true }
]
</script>

<template>
  <!-- legendMode defaults to the table; "compact" names the categories as chips. -->
  <CmkDonutChart :slices="slices" :format-value="formatBytes" legend-mode="table" />
</template>
