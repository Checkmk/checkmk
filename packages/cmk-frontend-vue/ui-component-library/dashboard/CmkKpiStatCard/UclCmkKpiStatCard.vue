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

import CmkKpiStatCard from '@/dashboard/components/CmkKpiStatCard'

import codeExample from './UclCmkKpiStatCardCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

// A window of per-minute values, oldest first (as the compute endpoint
// delivers them).
const SERIES = [
  62, 68, 75, 71, 66, 73, 82, 78, 74, 80, 88, 92, 85, 79, 83, 90, 95, 89, 84, 91, 97, 94, 87, 93,
  99, 96, 90, 95, 101, 98
]
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkKpiStatCard</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div style="display: flex; gap: 16px; flex-wrap: wrap">
        <!-- Neutral metric: the delta makes no judgment about direction. -->
        <div style="width: 280px; height: 130px">
          <CmkKpiStatCard
            value="801.84"
            unit="GB"
            :delta-ratio="0.062"
            :series="SERIES"
            color="var(--color-corporate-green-50)"
          />
        </div>
        <!-- "Up is bad" metric (e.g. alerts): an increase renders red. -->
        <div style="width: 280px; height: 130px">
          <CmkKpiStatCard
            value="48"
            :delta-ratio="0.12"
            delta-semantics="bad"
            :series="SERIES"
            color="var(--color-light-red-50)"
          />
        </div>
        <!-- Without a delta indicator. -->
        <div style="width: 280px; height: 130px">
          <CmkKpiStatCard
            value="3.20"
            unit="Gbps"
            :series="SERIES"
            color="var(--color-light-blue-50)"
          />
        </div>
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
