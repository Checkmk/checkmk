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
import { formatBytes } from '@/network-flow/format'

import codeExample from './UclCmkDonutChartCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

// Slices are provided pre-ranked and already include the aggregated "Other"
// slice; percentages are derived from the sum of all values.
const slices: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 4_720_000_000, color: 'blue' },
  { key: 'pops', label: 'POPS', value: 1_700_000_000, color: 'purple' },
  { key: 'imaps', label: 'IMAPS', value: 1_100_000_000, color: 'cyan' },
  { key: 'smtps', label: 'SMTPS', value: 900_000_000, color: 'magenta' },
  { key: 'unknown', label: 'Unknown', value: 760_000_000, color: 'orange' },
  { key: 'other', label: 'Other', value: 820_000_000, color: 'grey', isOther: true }
]
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDonutChart</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div style="width: 560px; height: 260px">
        <CmkDonutChart :slices="slices" :format-value="formatBytes" />
      </div>
    </UclDetailPageComponent>

    <!-- The tightest widget a dashboard allows. -->
    <UclDetailPageComponent>
      <div style="width: 320px; height: 180px">
        <CmkDonutChart :slices="slices" :format-value="formatBytes" />
      </div>
    </UclDetailPageComponent>

    <!-- The compact legend, at the size it exists for. -->
    <UclDetailPageComponent>
      <div style="width: 320px; height: 180px">
        <CmkDonutChart :slices="slices" :format-value="formatBytes" legend-mode="compact" />
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
