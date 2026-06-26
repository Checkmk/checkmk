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
import { ref } from 'vue'

import CmkChip from '@/components/CmkChip.vue'
import CmkChipSelect from '@/components/CmkChipSelect.vue'
import type { Suggestion, Suggestions } from '@/components/CmkSuggestions'
import { CmkTimeRangeTooltip } from '@/components/date-time'

defineProps<{ screenshotMode: boolean }>()

const selected = ref<string | null>(null)

const ranges: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: '1h', title: 'Last hour' },
    { name: '3h', title: 'Last 3 hours' },
    { name: '1d', title: 'Last day' },
    { name: '1w', title: 'Last week' }
  ]
}

const durationsBySeconds: Record<string, number> = {
  '1h': 3600,
  '3h': 10800,
  '1d': 86400,
  '1w': 604800
}

function durationFor(suggestion: Suggestion): number | undefined {
  return suggestion.name ? durationsBySeconds[suggestion.name] : undefined
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTimeRangeTooltip</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-time-range-tooltip__examples">
        <div class="ucl-cmk-time-range-tooltip__row">
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

        <CmkChipSelect
          v-model="selected"
          :options="ranges"
          input-hint="More ranges"
          label="time range"
        >
          <template #option="{ suggestion }">
            <CmkTimeRangeTooltip
              v-if="durationFor(suggestion) !== undefined"
              :duration-seconds="durationFor(suggestion)!"
            >
              <span class="ucl-cmk-time-range-tooltip__option">{{ suggestion.title }}</span>
            </CmkTimeRangeTooltip>
            <template v-else>{{ suggestion.title }}</template>
          </template>
        </CmkChipSelect>
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-time-range-tooltip__examples {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

.ucl-cmk-time-range-tooltip__row {
  display: flex;
  gap: var(--dimension-4);
}

/* Block trigger fills the row-spanning option wrapper, so the hover target is the whole option. */
.ucl-cmk-time-range-tooltip__option {
  display: block;
}
</style>
