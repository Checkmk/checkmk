<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
How the object is set up and what it sits between: its check, its neighbours in
the topology, the groups it belongs to and its labels.

A parent or child that is also on this map can be selected there -- following a
dependency on the map is usually what the operator wanted; the rest are names.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ObjectDetails } from '@/maps/types/api'

import { checkCommandLabel, configRows, labelEntries, topologyGroups } from '../contextFacts'
import DetailMetaList from './DetailMetaList.vue'

const props = defineProps<{
  details: ObjectDetails | null
  /** Host names on this map, which a topology entry can therefore lead to. */
  selectableHosts: string[]
}>()

const emit = defineEmits<{ 'select-host': [hostName: string] }>()

const { _t } = usei18n()

const rows = computed(() => configRows(props.details, _t))

// The check command reads better as monospace than as a grid cell: it is
// typically long and its parts matter.
const checkCommand = computed(
  () => rows.value.find((row) => row.label === checkCommandLabel(_t)) ?? null
)
const configFacts = computed(() => rows.value.filter((row) => row.label !== checkCommandLabel(_t)))

const topology = computed(() => topologyGroups(props.details, _t))
const labels = computed(() => labelEntries(props.details))

const selectable = computed(() => new Set(props.selectableHosts))
</script>

<template>
  <div class="maps-detail-context-tab">
    <DetailMetaList :rows="configFacts" />

    <div v-if="checkCommand">
      <div class="maps-detail-context-tab__heading">{{ checkCommand.label }}</div>
      <CmkCode :code-text="checkCommand.value" width="fill" />
    </div>

    <dl v-if="topology.length" class="maps-detail-context-tab__topology">
      <template v-for="group in topology" :key="group.label">
        <dt>{{ group.label }}</dt>
        <dd class="maps-detail-context-tab__chip-row">
          <CmkChip
            v-for="item in group.items"
            :key="item"
            size="small"
            :color="group.isHostList ? 'info' : 'others'"
            variant="outline"
            :as-div="!group.isHostList || !selectable.has(item)"
            @click="
              group.isHostList && selectable.has(item) ? emit('select-host', item) : undefined
            "
          >
            {{ item }}
          </CmkChip>
        </dd>
      </template>
    </dl>

    <div v-if="labels.length">
      <div class="maps-detail-context-tab__heading">{{ _t('Labels') }}</div>
      <div class="maps-detail-context-tab__chip-row">
        <CmkChip
          v-for="[key, value] in labels"
          :key="key"
          size="small"
          color="others"
          variant="outline"
          as-div
          :title="`${key}: ${value}`"
        >
          <template #start>
            <span class="maps-detail-context-tab__label-key">{{ key }}</span>
          </template>
          {{ value }}
        </CmkChip>
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-detail-context-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: 12px 16px;
}

.maps-detail-context-tab__heading {
  font-size: var(--font-size-small);
  text-transform: uppercase;
  color: var(--font-color-dimmed);
  letter-spacing: 0.04em;
  font-weight: var(--font-weight-bold);
  margin: 4px 0 6px;
}

/* Topology labels ("Contact groups") are long and their values are rows of
   chips, so each label gets its own line above them. */
.maps-detail-context-tab__topology {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
  margin: 0;
  font-size: 11px;
}

.maps-detail-context-tab__topology dt {
  color: var(--font-color-dimmed);
  text-transform: uppercase;
  font-size: var(--font-size-small);
  letter-spacing: 0.04em;
  margin-top: var(--dimension-3);
}

.maps-detail-context-tab__topology dd {
  margin: 0;
}

.maps-detail-context-tab__chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);
  margin: 0;
}

.maps-detail-context-tab__label-key {
  color: var(--font-color-dimmed);
  margin-right: var(--dimension-3);
}
</style>
