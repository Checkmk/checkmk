<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { inject } from 'vue'

import { ROW_DRAG_KEY } from '../MonitoringTableContext'
import BaseCell, { type CellVerticalAlign } from './BaseCell.vue'

const { _t } = usei18n()

defineProps<{
  columnId?: string | undefined
  verticalAlign?: CellVerticalAlign | undefined
}>()

const dragHandlers = inject(ROW_DRAG_KEY, null)
</script>

<template>
  <BaseCell
    class="monitoring-drag-handle-cell"
    :column-id="columnId"
    :vertical-align="verticalAlign"
  >
    <button
      v-if="dragHandlers"
      type="button"
      class="monitoring-drag-handle-cell__handle"
      :aria-label="_t('Drag to reorder')"
      :draggable="true"
      @dragstart="dragHandlers.dragStart"
      @drag="dragHandlers.drag"
      @dragend="dragHandlers.dragEnd"
    >
      <CmkIcon name="drag" size="small" style="pointer-events: none" />
    </button>
  </BaseCell>
</template>

<style scoped>
.monitoring-drag-handle-cell__handle {
  display: inline-flex;
  align-items: center;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  cursor: grab;

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }
}
</style>
