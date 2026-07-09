<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const props = defineProps<{
  selectedCount: number
  actions: CellAction[]
}>()

const emit = defineEmits<{
  (event: 'action', action: CellAction): void
}>()

const { _t, _tn } = usei18n()

const disabled = computed(() => props.selectedCount === 0)

const selectionLabel = computed(() =>
  _tn('%{count} host selected', '%{count} hosts selected', props.selectedCount, {
    count: props.selectedCount
  })
)

function select(action: CellAction): void {
  if (disabled.value || action.disabled) {
    return
  }
  emit('action', action)
}
</script>

<template>
  <div
    class="monitoring-action-bar"
    :class="{ 'monitoring-action-bar--disabled': disabled }"
    role="toolbar"
    :aria-label="_t('Actions for selected hosts')"
    :aria-disabled="disabled"
  >
    <span class="monitoring-action-bar__selection" aria-live="polite">{{ selectionLabel }}</span>
    <div class="monitoring-action-bar__actions">
      <CmkButton
        v-for="action in actions"
        :key="action.id"
        size="small"
        variant="optional"
        :disabled="disabled || action.disabled"
        :title="action.label"
        class="monitoring-action-bar__button"
        @click="select(action)"
      >
        <CmkIcon :name="action.icon" size="small" />
        {{ action.label }}
      </CmkButton>
    </div>
  </div>
</template>

<style scoped>
.monitoring-action-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  padding: var(--dimension-3) var(--dimension-4);
  border: 1px solid var(--ux-theme-4);
  border-radius: var(--border-radius);
  background: var(--ux-theme-2);
}

.monitoring-action-bar--disabled {
  opacity: 0.6;
}

.monitoring-action-bar__selection {
  flex: 0 0 auto;
  font-weight: var(--font-weight-bold);
}

.monitoring-action-bar__actions {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}

.monitoring-action-bar__button {
  gap: var(--dimension-2);
}
</style>
