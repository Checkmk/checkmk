<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

import { formatRelativeTimeRange } from './formatRelativeTimeRange'
import { useNowTicker } from './useNowTicker'
import { useResolvedDateTimeSettings } from './useResolvedDateTimeSettings'

const { durationSeconds, timeZone } = defineProps<{
  /** Length of the range ending "now", in seconds (e.g. last 4 hours -> 14400). */
  durationSeconds: number
  timeZone?: string
}>()

const open = ref(false)
const settings = useResolvedDateTimeSettings(undefined, () => timeZone)
// Re-reads the clock each minute while open, so the range stays current on a long hover.
const now = useNowTicker(open)
const rangeText = computed(() => formatRelativeTimeRange(now.value, durationSeconds, settings))
</script>

<template>
  <CmkTooltipProvider>
    <CmkTooltip :open="open" @update:open="open = $event">
      <!-- as-child: the default slot must be a single element (the chip / chip select). -->
      <CmkTooltipTrigger as-child>
        <slot />
      </CmkTooltipTrigger>
      <CmkTooltipContent side="top" align="center" :avoid-collisions="true">
        <span class="cmk-time-range-tooltip__content">{{ rangeText }}</span>
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>

<style scoped>
.cmk-time-range-tooltip__content {
  display: inline-block;
  padding: var(--dimension-3) var(--dimension-4);
  background-color: var(--ux-theme-5);
  color: var(--font-color);
  border: 1px solid var(--ux-theme-6);
  border-radius: var(--border-radius);
  font-size: var(--font-size-small);
  white-space: nowrap;
}
</style>
