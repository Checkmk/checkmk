<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import ActionButtons, { type CellAction } from './ActionButtons.vue'
import BaseCell, { type CellVerticalAlign } from './BaseCell.vue'

export type { CellAction }

withDefaults(
  defineProps<{
    actions: CellAction[]
    maxVisible?: number
    load?: (() => Promise<CellAction[]>) | undefined
    columnId?: string | undefined
    verticalAlign?: CellVerticalAlign | undefined
    /** A command picked here still runs. */
    busy?: boolean
  }>(),
  { maxVisible: 2, load: undefined, columnId: undefined, verticalAlign: undefined, busy: false }
)

const emit = defineEmits<{
  (event: 'select', action: CellAction): void
}>()
</script>

<template>
  <BaseCell class="monitoring-actions-cell" :column-id="columnId" :vertical-align="verticalAlign">
    <template #default>
      <ActionButtons
        class="monitoring-actions-cell__actions"
        :actions="actions"
        :max-visible="maxVisible"
        :load="load"
        :busy="busy"
        @select="emit('select', $event)"
      />
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-actions-cell__actions {
  margin-top: var(--dimension-2);
}
</style>
