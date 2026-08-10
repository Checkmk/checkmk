<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'

import CmkDonutChart, { type DonutSlice } from '@/network-flow/CmkDonutChart'

import codeExample from './UclCmkDonutChartCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

// Slices are provided pre-ranked and already include the aggregated "Other"
// slice; percentages are derived from the sum of all values.
const slices: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 47.2, color: 'blue' },
  { key: 'pops', label: 'POPS', value: 17.0, color: 'purple' },
  { key: 'imaps', label: 'IMAPS', value: 11.0, color: 'cyan' },
  { key: 'smtps', label: 'SMTPS', value: 9.0, color: 'magenta' },
  { key: 'unknown', label: 'Unknown', value: 7.6, color: 'orange' },
  { key: 'other', label: 'Other', value: 8.2, color: 'grey' }
]
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDonutChart</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div style="width: 320px; height: 180px">
        <CmkDonutChart :slices="slices" />
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
