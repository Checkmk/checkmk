<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkPerfometer from 'cmk-ui-library/components/CmkPerfometer.vue'

import type { Perfometer } from '../../api/types'
import BaseCell, { type CellLink } from './BaseCell.vue'

export interface PerfometerCellProps {
  data?: Perfometer | undefined
  stale?: boolean | undefined
  linkedTo?: CellLink | undefined
  button?: boolean | undefined
  columnId?: string | undefined
}

const props = defineProps<PerfometerCellProps>()

const emit = defineEmits<{
  (event: 'click', payload: MouseEvent): void
}>()
</script>

<template>
  <BaseCell
    :column-id="columnId"
    :linked-to="linkedTo"
    :button="button"
    @click="emit('click', $event)"
  >
    <template #default>
      <CmkPerfometer
        v-if="props.data"
        :class="{ 'monitoring-perfometer-cell--stale': stale }"
        :bars="props.data.bars"
        :formatted="props.data.formatted"
      />
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-perfometer-cell--stale {
  filter: saturate(0%);
}
</style>
