<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, inject } from 'vue'

import type { HostState, MonitoringIcon, ServiceState } from '../../api/types.ts'
import HostStateDisplay from '../HostStateDisplay.vue'
import { COLUMN_LAYOUT_KEY } from '../MonitoringTableContext'
import ServiceStateDisplay from '../ServiceStateDisplay.vue'
import StateModeIcons from '../StateModeIcons.vue'
import { SPELLED_OUT_EXTRA_WIDTH, STATE_COLUMN_MIN_WIDTH } from '../stateColumn'
import BaseCell from './BaseCell.vue'

interface BaseStateCellProps {
  stale?: boolean | undefined
  flapping?: boolean | undefined
  /** The state modes, picked and ordered by stateModes(). */
  modes?: readonly MonitoringIcon[] | undefined
  columnId?: string | undefined
}

export type StateCellProps = BaseStateCellProps &
  ({ kind?: 'host'; state: HostState } | { kind: 'service'; state: ServiceState })

const props = defineProps<StateCellProps>()

const columns = inject(COLUMN_LAYOUT_KEY, null)

// The column hugs the compact label and the icons of the fullest row: the spelled-out label
// fits once it is widened by the difference.
const spelledOutFrom = computed(
  () =>
    ((props.columnId ? columns?.value.get(props.columnId)?.minWidth : undefined) ??
      STATE_COLUMN_MIN_WIDTH) + SPELLED_OUT_EXTRA_WIDTH
)
</script>

<template>
  <BaseCell :column-id="columnId" :breakpoints="{ spelledOut: spelledOutFrom }">
    <template #default>
      <div class="monitoring-state-cell">
        <ServiceStateDisplay
          v-if="props.kind === 'service'"
          :state="props.state"
          :stale="stale"
          abbreviated
        />
        <HostStateDisplay v-else :state="props.state" :stale="stale" abbreviated />
        <StateModeIcons :flapping="flapping" :stale="stale" :modes="modes" />
      </div>
    </template>
    <template #spelledOut>
      <div class="monitoring-state-cell">
        <ServiceStateDisplay v-if="props.kind === 'service'" :state="props.state" :stale="stale" />
        <HostStateDisplay v-else :state="props.state" :stale="stale" />
        <StateModeIcons :flapping="flapping" :stale="stale" :modes="modes" />
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-state-cell {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-3);
  min-height: 21px;
  align-items: center;
  justify-content: center;
}
</style>
