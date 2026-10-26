<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One labelled set of state counts on a hover card, drawn like the monitoring
views draw a host's services.
-->
<script setup lang="ts">
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

export type StateCountTone = 'crit' | 'unknown' | 'warn' | 'pending' | 'ok'

export interface HoverStateCount {
  label: TranslatedString
  count: number
  tone: StateCountTone
  /** Deep-link into the filtered Checkmk view, or null when not linkable. */
  url: string | null
}

const COLOR: Record<StateCountTone, StateSegment['color']> = {
  ok: 'success',
  warn: 'warning',
  crit: 'danger',
  unknown: 'unknown',
  pending: 'pending'
}

const props = defineProps<{
  label: TranslatedString
  counts: HoverStateCount[]
}>()

const segments = computed<StateSegment[]>(() =>
  props.counts.map((entry) => ({
    label: entry.label,
    count: entry.count,
    color: COLOR[entry.tone],
    ...(entry.url ? { href: entry.url, target: '_blank' } : {})
  }))
)
</script>

<template>
  <CmkStateCountBar class="maps-hover-state-counts" :segments="segments" size="small">
    <template #heading>
      <span class="maps-hover-state-counts__label">{{ label }}</span>
    </template>
  </CmkStateCountBar>
</template>

<style scoped>
.maps-hover-state-counts {
  margin-top: var(--dimension-5);
}

.maps-hover-state-counts__label {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--font-color-dimmed);
}
</style>
