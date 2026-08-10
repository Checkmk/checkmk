<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDonutChart, { type DonutSlice } from '@/network-flow/CmkDonutChart'
import { formatBytes } from '@/network-flow/format'

const slices: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 4_720_000_000, color: 'blue' },
  { key: 'pops', label: 'POPS', value: 1_700_000_000, color: 'purple' },
  { key: 'other', label: 'Other', value: 3_580_000_000, color: 'grey' }
]
</script>

<template>
  <CmkDonutChart :slices="slices" :format-value="formatBytes" />
</template>
