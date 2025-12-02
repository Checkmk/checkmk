<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'

import CollapsibleContent from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import FilterItem from '@/dashboard-wip/components/Wizard/components/filter/WidgetObjectFilterConfiguration/FilterItem.vue'
import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'
import { FilterOrigin } from '@/dashboard-wip/types/filter'

const { _t } = usei18n()

interface Props {
  objectType: 'host' | 'service'
  filters: string[]
  getFilterValues: (filterId: string) => ConfiguredValues | null
  additionalItemLabel: string | null
  dashboardFilters: string[]
  dashboardConfiguredFilters: Record<string, ConfiguredValues>
  forceOverride: boolean
}

const props = defineProps<Props>()

const displayLabels = computed(() => {
  const capitalizedTitle = props.objectType.charAt(0).toUpperCase() + props.objectType.slice(1)
  return {
    title: _t('%{n} filters', { n: capitalizedTitle }),
    contextFilterTitle: _t('Applied filters'),
    emptyContextTitle: _t('No %{n} dashboard filters applied', { n: props.objectType }),
    emptyContextMessage: _t(
      `%{n} filters selected on dashboard level appear and apply to all widgets. You can override the values by setting widget specific or runtime filters. `,
      { n: capitalizedTitle }
    )
  }
})

const isOpen = ref(true)
const isAppliedOpen = ref(true)

const isOverridden = (filterId: string): boolean => {
  if (props.forceOverride) {
    return true
  }
  // A dashboard filter is overridden if a runtime filter with the same `filterId`
  // exists. The runtime filter takes precedence, even if it's not configured
  // with a value.
  return props.filters.includes(filterId)
}

const countDashboardFilters = computed(() => {
  return props.dashboardFilters.length
})
</script>

<template>
  <div class="dashboard-filter__collection">
    <div class="dashboard-filter__collection-title">
      <CmkLabel variant="title">{{ displayLabels.title }}</CmkLabel>
    </div>

    <CollapsibleTitle
      :title="displayLabels.contextFilterTitle"
      :open="isAppliedOpen"
      @toggle-open="isAppliedOpen = !isAppliedOpen"
    />
    <CollapsibleContent :open="isAppliedOpen">
      <div v-if="countDashboardFilters > 0" class="filter-list">
        <div v-for="filterId in dashboardFilters" :key="filterId" class="filter-item__wrapper">
          <FilterItem
            :origin="FilterOrigin.DASHBOARD"
            :filter-id="filterId"
            :configured-values="dashboardConfiguredFilters[filterId]!"
            :overridden="isOverridden(filterId)"
          />
        </div>
      </div>
      <div v-else class="dashboard-filter__empty-message">
        {{ displayLabels.emptyContextTitle }}
      </div>
    </CollapsibleContent>

    <div class="dashboard-filter__runtime-filters">
      <CollapsibleTitle
        :title="_t('Runtime filters')"
        :open="isOpen"
        @toggle-open="isOpen = !isOpen"
      />
      <CollapsibleContent :open="isOpen">
        <div v-for="(filterId, index) in filters" :key="index" class="filter-item__container">
          <slot
            :filter-id="filterId"
            :configured-filter-values="getFilterValues(filterId)"
            :index="index"
          />
        </div>
        <div v-if="additionalItemLabel" class="dashboard-filter__item-placeholder">
          <div class="db-runtime-filter-collection__item-placeholder-inner">
            {{ additionalItemLabel }}
          </div>
        </div>
      </CollapsibleContent>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__collection {
  margin-top: var(--dimension-7);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__collection-title {
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__applied-filters {
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-item__container {
  background-color: var(--ux-theme-3);
  margin-bottom: var(--dimension-4);
  border: 1px solid var(--ux-theme-8);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-item__wrapper {
  margin-bottom: var(--dimension-2);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__item-placeholder {
  padding: var(--dimension-5) var(--dimension-7);
  border: 1px solid var(--ux-theme-8);
  color: var(--color-white-50);
}

.db-runtime-filter-collection__item-placeholder-inner {
  border: var(--color-midnight-grey-40) var(--dimension-1) dashed;
  background-color: var(--color-midnight-grey-80);
  padding: var(--dimension-3);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__empty-message {
  padding: var(--dimension-5);
  color: var(--color-white-50);
}
</style>
