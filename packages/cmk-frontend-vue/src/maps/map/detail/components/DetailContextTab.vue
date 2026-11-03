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
import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'
import OverviewDetailList from '@/monitoring/shared/components/slide-in/OverviewDetailList.vue'
import { toNameItems } from '@/monitoring/shared/labels'

import { checkCommandLabel, configRows, labelItems, topologyGroups } from '../contextFacts'
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
const labels = computed(() => labelItems(props.details))

const selectable = computed(() => new Set(props.selectableHosts))
</script>

<template>
  <div class="maps-detail-context-tab">
    <DetailMetaList :rows="configFacts" />

    <div v-if="checkCommand">
      <div class="maps-detail-context-tab__heading">{{ checkCommand.label }}</div>
      <CmkCode :code-text="checkCommand.value" width="fill" />
    </div>

    <!-- Laid out like the overview in Checkmk's own slide-in. Parents and
         children on this map stay selectable, which only Maps can offer. -->
    <OverviewDetailList v-if="topology.length || labels.length" align="start">
      <template v-for="group in topology" :key="group.label">
        <dt>{{ group.label }}</dt>
        <dd v-if="group.isHostList" class="maps-detail-context-tab__chip-row">
          <CmkChip
            v-for="item in group.items"
            :key="item"
            size="small"
            color="info"
            variant="outline"
            :as-div="!selectable.has(item)"
            @click="selectable.has(item) ? emit('select-host', item) : undefined"
          >
            {{ item }}
          </CmkChip>
        </dd>
        <dd v-else>
          <OverviewChips :items="toNameItems(group.items)" />
        </dd>
      </template>
      <template v-if="labels.length">
        <dt>{{ _t('Labels') }}</dt>
        <dd>
          <OverviewChips :items="labels" />
        </dd>
      </template>
    </OverviewDetailList>
  </div>
</template>

<style scoped>
.maps-detail-context-tab {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding: var(--dimension-5) var(--dimension-6);
}

.maps-detail-context-tab__heading {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  font-weight: var(--font-weight-medium);
  margin: var(--dimension-3) 0 var(--dimension-4);
}

.maps-detail-context-tab__chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);
  margin: 0;
}
</style>
