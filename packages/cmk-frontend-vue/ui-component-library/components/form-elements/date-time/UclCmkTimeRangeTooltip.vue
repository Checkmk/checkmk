<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import codeExample from './UclCmkTimeRangeTooltipCodeExample.vue?raw'
</script>

<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'

import CmkChip from '@/components/CmkChip.vue'
import { CmkTimeRangeTooltip } from '@/components/date-time'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTimeRangeTooltip</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-time-range-tooltip__examples">
        <CmkTimeRangeTooltip :duration-seconds="14400">
          <CmkChip color="others" variant="outline">Last 4 hours</CmkChip>
        </CmkTimeRangeTooltip>
        <CmkTimeRangeTooltip :duration-seconds="86400">
          <CmkChip color="others" variant="outline">Last day</CmkChip>
        </CmkTimeRangeTooltip>
        <CmkTimeRangeTooltip :duration-seconds="604800">
          <CmkChip color="others" variant="outline">Last week</CmkChip>
        </CmkTimeRangeTooltip>
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-time-range-tooltip__examples {
  display: flex;
  gap: var(--dimension-4);
}
</style>
