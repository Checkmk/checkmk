<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { VisibilityState } from '@tanstack/vue-table'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject, ref } from 'vue'

import { MONITORING_SERVICE } from '../MonitoringTableContext'
import FilterSearchInput from './FilterSearchInput.vue'
import type { ColumnVisibilityFilter } from './types'

defineProps<{ definition: ColumnVisibilityFilter }>()

const draft = defineModel<VisibilityState>()

const { _t } = usei18n()

const monitoringService = inject(MONITORING_SERVICE, null)

const staged = computed<VisibilityState>(
  () => draft.value ?? monitoringService?.defaultColumnVisibility ?? {}
)

const searchText = ref('')

interface VisibilityRow {
  id: string
  label: string
  visible: boolean
}

const rows = computed<VisibilityRow[]>(() => {
  if (!monitoringService) {
    return []
  }
  return monitoringService.toggleableColumns.map((column) => ({
    id: column.id,
    label: column.label,
    visible: staged.value[column.id] !== false
  }))
})

const visibleRows = computed<VisibilityRow[]>(() => {
  const needle = searchText.value.trim().toLowerCase()
  if (!needle) {
    return rows.value
  }
  return rows.value.filter((row) => row.label.toLowerCase().includes(needle))
})

function setVisible(id: string, visible: boolean): void {
  draft.value = { ...staged.value, [id]: visible }
}
</script>

<template>
  <div class="monitoring-filter-column-visibility">
    <FilterSearchInput v-model="searchText" />

    <div class="monitoring-filter-column-visibility__options">
      <button
        v-for="row in visibleRows"
        :key="row.id"
        type="button"
        class="monitoring-filter-column-visibility__row"
        :aria-pressed="row.visible"
        @click="setVisible(row.id, !row.visible)"
      >
        <CmkMultitoneIcon
          :name="row.visible ? 'eye' : 'eye-crossed-out'"
          :primary-color="{ custom: 'var(--color-mist-grey-60)' }"
          aria-hidden="true"
          style="pointer-events: none"
        />
        <span class="monitoring-filter-column-visibility__label">{{ row.label }}</span>
      </button>

      <p v-if="visibleRows.length === 0" class="monitoring-filter-column-visibility__empty">
        {{ _t('No matching columns') }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.monitoring-filter-column-visibility {
  display: flex;
  flex-direction: column;
}

.monitoring-filter-column-visibility__options {
  display: flex;
  flex-direction: column;
  max-height: 240px;
  overflow-y: auto;
}

.monitoring-filter-column-visibility__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  border: 0;
  background-color: transparent;
  padding: var(--dimension-2);
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;

  &:hover,
  &:focus-within,
  &:focus-visible {
    background-color: var(--ux-theme-3);
  }
}

.monitoring-filter-column-visibility__row[aria-pressed='false']
  .monitoring-filter-column-visibility__label {
  opacity: 0.6;
}

.monitoring-filter-column-visibility__empty {
  padding: var(--dimension-2) var(--dimension-4);
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
