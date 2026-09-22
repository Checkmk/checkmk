<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { VisibilityState } from '@tanstack/vue-table'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import ArrowDown from 'cmk-ui-library/components/graphics/ArrowDown.vue'
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
      <CmkButton
        variant="optional"
        size="small"
        class="monitoring-column-picker__trigger"
        :class="{ 'monitoring-column-picker__trigger--active': isOpen }"
        :title="_t('Show or hide columns')"
        :aria-label="_t('Show or hide columns')"
        :aria-expanded="isOpen"
        :aria-controls="panelId"
        @click="toggle"
      >
        <CmkMultitoneIcon
          name="columns"
          :primary-color="{ custom: 'var(--color-light-blue-20)' }"
          :secondary-color="{ custom: 'var(--color-corporate-green-70)' }"
          aria-hidden="true"
        />
        <ArrowDown
          class="monitoring-column-picker__dropdown-icon"
          :class="{ 'monitoring-column-picker__dropdown-icon--rotated': isOpen }"
          aria-hidden="true"
        />
      </CmkButton>
    </template>
  </FilterDropdown>
</template>

<style scoped>
.monitoring-column-picker__trigger {
  gap: var(--dimension-2);
  padding: 0 var(--dimension-3, 4px);
}

.monitoring-column-picker__dropdown-icon {
  width: 8px;
  height: 8px;

  &.monitoring-column-picker__dropdown-icon--rotated {
    transform: rotate(180deg);
  }
}
</style>
