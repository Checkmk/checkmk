<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One set of state counts, drawn like the monitoring views draw a host's services:
on the hover cards and in the slide-in alike.
-->
<script setup lang="ts">
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

export type StateCountTone = 'crit' | 'unknown' | 'warn' | 'pending' | 'ok'

export interface MapStateCount {
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
  label?: TranslatedString | undefined
  counts: MapStateCount[]
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
  <CmkStateCountBar :segments="segments" size="small">
    <template v-if="label" #heading>
      <CmkHeading type="h4">{{ label }}</CmkHeading>
    </template>
  </CmkStateCountBar>
</template>
