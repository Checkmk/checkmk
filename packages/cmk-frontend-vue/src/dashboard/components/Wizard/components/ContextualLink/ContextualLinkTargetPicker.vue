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
import { type VisualCopy, useCopyOptions } from '@/dashboard/components/selectors/visualKey'

import {
  type DashboardTarget,
  dashboardCopyOptions,
  fetchDashboardTargets
} from '../WidgetVisualization/api'
import type { VisualLocation } from './contextualLink'

const { _t } = usei18n()

const { singleInfos } = defineProps<{
  // The objects a click names; a target restricted to others would open incomplete.
  singleInfos: string[]
}>()
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

const selectedCopy = computed<VisualCopy | null>({
  get: () =>
    target.value?.type === targetType.value
      ? { name: target.value.name, owner: target.value.owner }
      : null,
  set: (copy) => {
    target.value = copy === null ? null : { type: targetType.value, ...copy }
  }
})

const offeredDashboards = computed(() =>
  dashboards.value.filter((dashboard) =>
    dashboard.restrictedToSingle.every((info) => singleInfos.includes(info))
  )
)
const { suggestions: dashboardOptions, key: dashboardKey } = useCopyOptions(selectedCopy, () =>
  dashboardCopyOptions(offeredDashboards.value)
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
      v-model:selected-copy="selectedCopy"
      :read-only="false"
      by-owner
      :single-infos="singleInfos"
    />
    <template v-else>
      <div v-if="dashboardsError" class="error-message">
        {{ _t('Error loading dashboards: ') + dashboardsError }}
      </div>
      <CmkDropdown
        v-else
        v-model="dashboardKey"
        :label="_t('Select a target')"
        :options="{ type: 'filtered', suggestions: dashboardOptions }"
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
