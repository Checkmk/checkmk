<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n.ts'

import CmkButton from '@/components/CmkButton.vue'

import type { useFilters } from '@/dashboard-wip/components/filter/composables/useFilters.ts'
import type { FilterDefinition } from '@/dashboard-wip/components/filter/types.ts'

import FilterSelectionCollection from './FilterSelectionCollection.vue'

const { _t } = usei18n()
const props = defineProps<{
  filterDefinitions: Record<string, FilterDefinition>
  runtimeFilters: ReturnType<typeof useFilters>
}>()

const emit = defineEmits<{
  'save-runtime-filters': []
  'cancel-runtime-filters': []
  'set-configuration-target': [target: 'runtime-filter']
}>()

const hostRuntimeFilters = computed(() => {
  const filters: string[] = []
  props.runtimeFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = props.filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'host') {
      filters.push(filterId)
    }
  })
  return filters
})

const serviceRuntimeFilters = computed(() => {
  const filters: string[] = []
  props.runtimeFilters.activeFilters.value?.forEach((filterId) => {
    const filterDef = props.filterDefinitions[filterId]
    if (filterDef && filterDef.extensions.info === 'service') {
      filters.push(filterId)
    }
  })
  return filters
})

const saveRuntimeFilters = () => {
  emit('save-runtime-filters')
}

const cancelConfiguration = () => {
  emit('cancel-runtime-filters')
  emit('set-configuration-target', 'runtime-filter')
}
</script>

<template>
  <div class="runtime-filters-content">
    <div class="filter-configuration__apply">
      <CmkButton variant="primary" @click="saveRuntimeFilters">
        {{ _t('Save') }}
      </CmkButton>
      <CmkButton variant="secondary" @click="cancelConfiguration"> {{ _t('Cancel') }}</CmkButton>
    </div>

    <div class="runtime-filters-content__body">
      <FilterSelectionCollection
        :title="_t('Host filter')"
        :filters="hostRuntimeFilters"
        :filter-definitions="filterDefinitions"
        @remove-filter="runtimeFilters.removeFilter"
      />
      <FilterSelectionCollection
        :title="_t('Service filter')"
        :filters="serviceRuntimeFilters"
        :filter-definitions="filterDefinitions"
        @remove-filter="runtimeFilters.removeFilter"
      />
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.runtime-filters-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-configuration__apply {
  display: flex;
  align-items: center;
  margin-bottom: var(--dimension-5);
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.runtime-filters-content__body {
  flex: 1;
  margin-bottom: var(--dimension-4);
  overflow-y: auto;
}
</style>
