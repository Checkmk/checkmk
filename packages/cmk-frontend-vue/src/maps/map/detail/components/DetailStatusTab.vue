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
import { computed } from 'vue'

import MapStateCounts, { type MapStateCount } from '@/maps/map/components/MapStateCounts.vue'
import type { MapElement, ObjectDetails, ObjectState } from '@/maps/types/api'
import { stateExclusion } from '@/maps/utils/memberFilter'

import { checkInfoRows, identityRows, stateModifiers } from '../statusFacts'
import DetailHostChips from './DetailHostChips.vue'
import DetailMetaList from './DetailMetaList.vue'
import DetailStateBadges from './DetailStateBadges.vue'

const props = defineProps<{
  object: MapElement
  state: ObjectState
  details: ObjectDetails | null
  displayName: string
  checkmkUrl: string | null | undefined
  /** Per-state counts of the hosts behind this object, where it has any. */
  hostChips: MapStateCount[]
  /** Per-state counts of the services behind it. */
  serviceChips: MapStateCount[]
  /** Ticks once a second so the ageing labels move on their own. */
  nowMs: number
  /** Host names on this map, which a parent named here can therefore lead to. */
  selectableHosts: string[]
  /** Hosts known to be up: no parent the host is cut off through. */
  hostsUp?: ReadonlySet<string> | undefined
}>()

const emit = defineEmits<{ 'select-host': [hostName: string] }>()

const { _t } = usei18n()

const modifiers = computed(() => stateModifiers(props.state, props.details))

const uncounted = computed(() =>
  props.hostChips.length || props.serviceChips.length ? stateExclusion(props.object) : null
)

// An unreachable host's own output says little: what to look at is the parent
// that cut it off.
const reachedThrough = computed(() =>
  props.state.state === 'UNREACHABLE'
    ? (props.details?.parents ?? []).filter((parent) => !props.hostsUp?.has(parent))
    : []
)

const facts = computed(() => [
  ...identityRows(props.object, props.state, props.displayName, props.checkmkUrl, _t),
  ...checkInfoRows(props.object, props.state, props.details, props.nowMs, _t)
])
</script>

<template>
  <div class="maps-detail-status-tab">
    <DetailStateBadges :modifiers="modifiers" />

    <pre v-if="state.output" class="maps-detail-status-tab__output">{{ state.output }}</pre>

    <div v-if="reachedThrough.length" class="maps-detail-status-tab__reached-through">
      <span>{{ _t('Unreachable through') }}</span>
      <DetailHostChips
        :hosts="reachedThrough"
        :selectable-hosts="selectableHosts"
        @select-host="emit('select-host', $event)"
      />
    </div>

    <MapStateCounts v-if="hostChips.length" :counts="hostChips" :label="_t('Hosts')" />
    <MapStateCounts v-if="serviceChips.length" :counts="serviceChips" :label="_t('Services')" />
    <p v-if="uncounted" class="maps-detail-status-tab__uncounted">
      {{ _t('Members matching "%{pattern}" are not counted.', { pattern: uncounted }) }}
    </p>

    <DetailMetaList :rows="facts" />

    <slot name="aggregation" />
  </div>
</template>

<style scoped>
.maps-detail-status-tab {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding: var(--dimension-5) var(--dimension-6);
}

.maps-detail-status-tab__output {
  font-family: monospace;
  font-size: var(--font-size-normal);
  background: var(--ux-theme-1);
  color: var(--font-color);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  padding: var(--dimension-4) var(--dimension-5);
  margin: var(--dimension-3) 0 0;
  overflow: auto;
  white-space: pre-wrap;
  max-height: 180px;
}

.maps-detail-status-tab__reached-through {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3);
}

.maps-detail-status-tab__uncounted {
  margin: 0;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  overflow-wrap: anywhere;
}
</style>
