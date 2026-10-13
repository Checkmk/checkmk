<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What is wrong, in the order an operator asks it: what qualifies the state, what
the check said, how the things underneath are doing, and who this object is.

The plugin output comes first and verbatim -- it is the one piece of text the
person who wrote the check meant for this moment.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { MapElement, ObjectDetails, ObjectState } from '@/maps/types/api'

import type { SummaryChip } from '../composables/useSummaryChips'
import { checkInfoRows, identityRows, stateModifiers } from '../statusFacts'
import DetailChipGrid, { type DetailChip } from './DetailChipGrid.vue'
import DetailMetaList from './DetailMetaList.vue'
import DetailStateBadges from './DetailStateBadges.vue'

const props = defineProps<{
  object: MapElement
  state: ObjectState
  details: ObjectDetails | null
  displayName: string
  checkmkUrl: string | null | undefined
  /** Per-state counts of the hosts behind this object, where it has any. */
  hostChips: SummaryChip[]
  /** Per-state counts of the services behind it. */
  serviceChips: SummaryChip[]
  /** What the service counts are counting -- hosts, for a host group. */
  serviceChipsLabel: TranslatedString
  /** Ticks once a second so the ageing labels move on their own. */
  nowMs: number
}>()

const { _t } = usei18n()

const modifiers = computed(() => stateModifiers(props.state, props.details))

const facts = computed(() => [
  ...identityRows(props.object, props.state, props.displayName, props.checkmkUrl, _t),
  ...checkInfoRows(props.object, props.state, props.details, props.nowMs, _t)
])

function asChips(chips: SummaryChip[]): DetailChip[] {
  return chips.map((chip) => ({
    key: chip.state,
    label: chip.label,
    count: chip.count,
    tone: chip.tone,
    url: chip.url
  }))
}
</script>

<template>
  <div class="maps-detail-status-tab">
    <DetailStateBadges :modifiers="modifiers" />

    <pre v-if="state.output" class="maps-detail-status-tab__output">{{ state.output }}</pre>

    <DetailChipGrid :chips="asChips(hostChips)" :label="_t('Hosts')" />
    <DetailChipGrid :chips="asChips(serviceChips)" :label="serviceChipsLabel" />

    <DetailMetaList :rows="facts" />

    <slot name="aggregation" />
  </div>
</template>

<style scoped>
.maps-detail-status-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: 12px 16px;
}

.maps-detail-status-tab__output {
  font-family: monospace;
  font-size: 11px;
  background: var(--ux-theme-1);
  color: var(--font-color);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  padding: 8px 10px;
  margin: 4px 0 0;
  overflow: auto;
  white-space: pre-wrap;
  max-height: 180px;
}
</style>
