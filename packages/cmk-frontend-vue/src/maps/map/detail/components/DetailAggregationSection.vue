<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Why a BI aggregation is in the state it is in: the counts of its leaves, the
worst one by name, and the leaves themselves as a list to drill into.

Two ways to read it. "Summary" cuts the tree at the depth the map object asks
for, so a wide aggregation stays readable; "Details" lists the real leaves,
which is the only view where naming a single worst leaf means anything.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { AggregationLeafRow, AggregationSummary } from '../composables/useAggregationDetail'
import type { SummaryChip } from '../composables/useSummaryChips'
import DetailChipGrid, { type DetailChip } from './DetailChipGrid.vue'

const props = defineProps<{
  summary: AggregationSummary
  chips: SummaryChip[]
  view: 'summary' | 'details'
  viewOptions: { value: string; label: string }[]
  /** Whether the map object asks for a cut tree at all. */
  canSwitchView: boolean
  rows: AggregationLeafRow[]
  /** Whether the rows come from more than one host, so they need naming. */
  multiHost: boolean
  /** Real hosts/services below this aggregation that could be acknowledged. */
  problemLeafCount: number
  /** Whether this operator may acknowledge in the first place. */
  canAcknowledge: boolean
  /** Whether livestatus to a federated site went dead since the tree was read. */
  stale: boolean
}>()

const emit = defineEmits<{
  'update:view': [view: string]
  'pick-leaf': [row: AggregationLeafRow]
  'bulk-acknowledge': []
}>()

const { _t } = usei18n()

// A dropdown rather than a toggle group: the drawer is 360px wide and
// CmkToggleButtonGroup is the form-scale control (150px per option), so even
// two options cannot sit beside the heading. The labels arrive translated.
const viewChoices = computed(() => ({
  type: 'fixed' as const,
  suggestions: props.viewOptions.map((option) => ({
    name: option.value,
    title: untranslated(option.label)
  }))
}))

const summaryChips = computed<DetailChip[]>(() =>
  props.chips.map((chip) => ({
    key: chip.state,
    label: chip.label,
    count: chip.count,
    tone: chip.tone
  }))
)
</script>

<template>
  <section class="maps-detail-aggregation-section">
    <div class="maps-detail-aggregation-section__head">
      <h3 class="maps-detail-aggregation-section__heading">{{ _t('Aggregation') }}</h3>
      <CmkDropdown
        v-if="canSwitchView"
        class="maps-detail-aggregation-section__view"
        :model-value="view"
        :options="viewChoices"
        :label="_t('Aggregation view')"
        @update:model-value="$event && emit('update:view', $event)"
      />
    </div>

    <DetailChipGrid :chips="summaryChips" />

    <!-- Only the details view lists real leaves; naming a "worst leaf" from a
         tree that was cut at a depth would point at something that is not one. -->
    <div
      v-if="view === 'details' && summary.worstPath"
      class="maps-detail-aggregation-section__row-text"
    >
      {{ _t('Worst leaf') }}:
      <span class="maps-detail-aggregation-section__strong">{{ summary.worstPath }}</span>
      <div v-if="summary.worstOutput" class="maps-detail-aggregation-section__worst-output">
        {{ summary.worstOutput }}
      </div>
    </div>
    <div v-if="view === 'summary'" class="maps-detail-aggregation-section__intro">
      {{
        _t('%{count} nodes at depth %{depth} below the root.', {
          count: summary.treeRows.length,
          depth: summary.treeDepth
        })
      }}
    </div>

    <!-- Say it outright: a dead federation link means the leaf states below
         may be describing the past, and "1 CRIT" would be misread as now. -->
    <div v-if="stale" class="maps-detail-aggregation-section__stale">
      {{ untranslated('⚠') }}
      {{
        _t(
          'Connection to at least one federation site is unhealthy — leaf states shown may be out of date.'
        )
      }}
    </div>

    <button
      v-if="problemLeafCount > 0 && canAcknowledge"
      type="button"
      class="maps-detail-aggregation-section__bulk"
      @click="emit('bulk-acknowledge')"
    >
      {{ _t('Acknowledge %{count} contributing leaves', { count: problemLeafCount }) }}
    </button>

    <ul v-if="rows.length" class="maps-detail-aggregation-section__list">
      <li
        v-for="row in rows"
        :key="row.id"
        class="maps-detail-aggregation-section__row"
        :class="row.hostName ? 'maps-detail-aggregation-section__row--clickable' : ''"
        :title="row.output || undefined"
        :role="row.hostName ? 'button' : undefined"
        :tabindex="row.hostName ? 0 : undefined"
        @click="emit('pick-leaf', row)"
        @keydown.enter.prevent="emit('pick-leaf', row)"
        @keydown.space.prevent="emit('pick-leaf', row)"
      >
        <span
          class="maps-detail-aggregation-section__dot"
          :class="`maps-detail-aggregation-section__dot--${row.tone}`"
        />
        <span class="maps-detail-aggregation-section__row-text">
          <span
            v-if="multiHost && row.hostName && row.serviceDescription"
            class="maps-detail-aggregation-section__host"
            >{{ row.hostName }} ·
          </span>
          {{ row.label }}
        </span>
        <span class="maps-detail-aggregation-section__state">{{ row.stateLabel }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.maps-detail-aggregation-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-detail-aggregation-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  flex-wrap: wrap;
}

/* The head is a wrapping flex row; the switch takes the width it needs and
   drops to its own line rather than squeezing the heading. */
.maps-detail-aggregation-section__view {
  flex: 1;
  min-width: 140px;
}

.maps-detail-aggregation-section__heading {
  margin: 0;
  font-size: var(--font-size-small);
  text-transform: uppercase;
  color: var(--font-color-dimmed);
  letter-spacing: 0.04em;
  font-weight: var(--font-weight-bold);
}

.maps-detail-aggregation-section__intro {
  color: var(--font-color-dimmed);
  font-size: 11px;
}

.maps-detail-aggregation-section__stale {
  color: var(--color-state-warning);
  font-style: italic;
  font-size: 11px;
}

.maps-detail-aggregation-section__bulk {
  align-self: flex-start;
  font: inherit;
  font-size: 11px;
  cursor: pointer;
  color: var(--font-color);
  background: var(--ux-theme-1);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  padding: 4px 8px;
}

.maps-detail-aggregation-section__bulk:hover {
  background: var(--input-hover-bg-color);
}

.maps-detail-aggregation-section__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.maps-detail-aggregation-section__row {
  display: grid;
  grid-template-columns: 8px 1fr auto;
  align-items: center;
  gap: var(--dimension-4);
  background: var(--ux-theme-1);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  padding: 6px 8px;
  font-size: 11px;
}

.maps-detail-aggregation-section__row--clickable {
  cursor: pointer;
}

.maps-detail-aggregation-section__row--clickable:hover {
  background: var(--input-hover-bg-color);
}

.maps-detail-aggregation-section__row--clickable:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

.maps-detail-aggregation-section__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--font-color-dimmed);
}

.maps-detail-aggregation-section__dot--ok {
  background: var(--color-state-ok);
}

.maps-detail-aggregation-section__dot--warn {
  background: var(--color-state-warning);
}

.maps-detail-aggregation-section__dot--crit {
  background: var(--color-state-critical);
}

.maps-detail-aggregation-section__dot--unknown {
  background: var(--color-state-unknown);
}

.maps-detail-aggregation-section__row-text {
  color: var(--font-color);
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.maps-detail-aggregation-section__strong {
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

/* The worst leaf's own plugin output, so the reason is readable without
   drilling into the leaf. */
.maps-detail-aggregation-section__worst-output {
  margin-top: var(--dimension-2);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  overflow-wrap: anywhere;
}

/* Host prefix on the service leaves of a multi-host aggregation. */
.maps-detail-aggregation-section__host {
  color: var(--font-color-dimmed);
}

.maps-detail-aggregation-section__state {
  font-family: monospace;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
