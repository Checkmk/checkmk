<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import SelectorView from '@/dashboard/components/selectors/SelectorView.vue'
import { withStoredName } from '@/dashboard/components/selectors/storedName'

import {
  type DashboardTarget,
  dashboardOptions,
  fetchDashboardTargets
} from '../WidgetVisualization/api'
import type { VisualLocation } from './contextualLink'

const { _t } = usei18n()

const target = defineModel<VisualLocation | null>({ required: true })

const targetType = ref<VisualLocation['type']>(target.value?.type ?? 'views')
const dashboards = ref<DashboardTarget[]>([])
const dashboardsError = ref<string | null>(null)

// Loaded once, and only when the dashboards are actually offered.
watch(
  targetType,
  async (type) => {
    if (type !== 'dashboards' || dashboards.value.length > 0) {
      return
    }
    dashboardsError.value = null
    try {
      dashboards.value = await fetchDashboardTargets()
    } catch (error: unknown) {
      dashboardsError.value = String(error)
    }
  },
  { immediate: true }
)

const typeOptions = computed(() => [
  { name: 'views', title: _t('Views') },
  { name: 'dashboards', title: _t('Dashboards') }
])

const selectedType = computed<string | null>({
  get: () => targetType.value,
  set: (value) => {
    targetType.value = value as VisualLocation['type']
    target.value = null
  }
})

const selectedName = computed<string | null>({
  get: () => (target.value?.type === targetType.value ? target.value.name : null),
  set: (name) => {
    target.value = name === null ? null : { type: targetType.value, name }
  }
})

const dashboardSuggestions = computed(() =>
  withStoredName(dashboardOptions(dashboards.value), selectedName.value)
)
</script>

<template>
  <div class="db-contextual-link-target-picker">
    <CmkDropdown
      v-model="selectedType"
      :label="_t('Select a category')"
      :options="{ type: 'fixed', suggestions: typeOptions }"
    />
    <SelectorView
      v-if="targetType === 'views'"
      v-model:selected-view="selectedName"
      :read-only="false"
    />
    <template v-else>
      <div v-if="dashboardsError" class="error-message">
        {{ _t('Error loading dashboards: ') + dashboardsError }}
      </div>
      <CmkDropdown
        v-else
        v-model="selectedName"
        :label="_t('Select a target')"
        :options="{ type: 'filtered', suggestions: dashboardSuggestions }"
      />
    </template>
  </div>
</template>

<style scoped>
.db-contextual-link-target-picker {
  display: flex;
  gap: var(--dimension-6);
}
</style>
