<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { VisibilityState } from '@tanstack/vue-table'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { inject, ref, watch } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import { MONITORING_SERVICE } from './MonitoringTableContext'
import FilterDropdown from './filter/FilterDropdown.vue'
import type { ColumnVisibilityFilter } from './filter/types'

const { _t } = usei18n()

const monitoringService = inject(MONITORING_SERVICE, null)

const definition: ColumnVisibilityFilter = { type: 'column-visibility' }

const model = ref<ColumnFilterNode<FilterField> | undefined>({
  ...monitoringService?.columnVisibility.value
} as unknown as ColumnFilterNode<FilterField>)

watch(model, (value) => {
  if (!monitoringService) {
    return
  }
  const visibility = value as unknown as VisibilityState | undefined
  if (visibility === undefined) {
    monitoringService.resetColumnVisibility()
  } else {
    monitoringService.updateColumnVisibility(visibility)
  }
})
</script>

<template>
  <FilterDropdown
    v-model="model"
    :definition="definition"
    :label="_t('columns')"
    :clear-label="_t('Back to default')"
  >
    <template #trigger="{ toggle, isOpen, panelId }">
      <button
        type="button"
        class="monitoring-column-picker__trigger"
        :class="{ 'monitoring-column-picker__trigger--active': isOpen }"
        :title="_t('Show or hide columns')"
        :aria-label="_t('Show or hide columns')"
        :aria-expanded="isOpen"
        :aria-controls="panelId"
        @click="toggle"
      >
        <CmkMultitoneIcon
          name="setup"
          :primary-color="{ custom: 'var(--success)' }"
          aria-hidden="true"
        />
      </button>
    </template>
  </FilterDropdown>
</template>

<style scoped>
.monitoring-column-picker__trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background-color: transparent;
  padding: 0;
  color: inherit;
  cursor: pointer;

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }
}
</style>
