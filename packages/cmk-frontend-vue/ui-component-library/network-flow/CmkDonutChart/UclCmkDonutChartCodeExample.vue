<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDonutChart, { type DonutSlice } from '@/network-flow/CmkDonutChart'

const slices: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 47.2, color: 'blue' },
  { key: 'pops', label: 'POPS', value: 17.0, color: 'purple' },
  { key: 'other', label: 'Other', value: 35.8, color: 'grey' }
]
</script>

<template>
  <CmkDonutChart :slices="slices" />
</template>
