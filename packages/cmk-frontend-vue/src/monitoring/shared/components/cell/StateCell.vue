<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostState, ServiceState } from '../../api/types.ts'
import HostStateDisplay from '../HostStateDisplay.vue'
import ServiceStateDisplay from '../ServiceStateDisplay.vue'
import BaseCell from './BaseCell.vue'

interface BaseStateCellProps {
  stale?: boolean | undefined
  pending?: boolean | undefined
  columnId?: string | undefined
}

export type StateCellProps = BaseStateCellProps &
  ({ kind?: 'host'; state: HostState } | { kind: 'service'; state: ServiceState })

/** The column width from which a spelled-out state label fits beside its icons. */
const SPELLED_OUT_LABEL_WIDTH = 131

const { _t } = usei18n()

const props = defineProps<StateCellProps>()
</script>

<template>
  <BaseCell :column-id="columnId" :breakpoints="{ spelledOut: SPELLED_OUT_LABEL_WIDTH }">
    <template #default>
      <div class="monitoring-state-cell">
        <ServiceStateDisplay
          v-if="props.kind === 'service'"
          :state="props.state"
          :pending="pending"
          :stale="stale"
          abbreviated
        />
        <HostStateDisplay
          v-else
          :state="props.state"
          :pending="pending"
          :stale="stale"
          abbreviated
        />
        <CmkMultitoneIcon
          v-if="stale"
          class="monitoring-state-cell__mode-icon"
          name="stale"
          primary-color="font"
          :title="_t('Stale')"
        />
      </div>
    </template>
    <template #spelledOut>
      <div class="monitoring-state-cell">
        <ServiceStateDisplay
          v-if="props.kind === 'service'"
          :state="props.state"
          :pending="pending"
          :stale="stale"
        />
        <HostStateDisplay v-else :state="props.state" :pending="pending" :stale="stale" />
        <CmkMultitoneIcon
          v-if="stale"
          class="monitoring-state-cell__mode-icon"
          name="stale"
          primary-color="font"
          :title="_t('Stale')"
        />
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-state-cell {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-3);
  align-items: center;
  justify-content: center;
}

.monitoring-state-cell__mode-icon {
  width: var(--dimension-6);
  height: var(--dimension-6);
}
</style>
