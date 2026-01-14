<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import CollapsibleContent from '@/dashboard/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import FilterItem from '@/dashboard/components/Wizard/components/filter/WidgetObjectFilterConfiguration/FilterItem.vue'
import type { ConfiguredValues } from '@/dashboard/components/filter/types.ts'
import { FilterOrigin } from '@/dashboard/types/filter'

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
    emptyContextTitle: _t('No default %{n} filters applied', { n: props.objectType }),
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
  <div>
    <CmkHeading type="h3">
      {{ displayLabels.title }}
    </CmkHeading>

    <div class="db-runtime-filter-collection__filter-container">
      <CollapsibleTitle
        :title="displayLabels.contextFilterTitle"
        :open="isAppliedOpen"
        @toggle-open="isAppliedOpen = !isAppliedOpen"
      />
      <CollapsibleContent :open="isAppliedOpen">
        <div class="db-runtime-filter-collection__items">
          <template v-if="countDashboardFilters > 0">
            <div v-for="filterId in dashboardFilters" :key="filterId" class="filter-item__wrapper">
              <FilterItem
                :origin="FilterOrigin.DASHBOARD"
                :filter-id="filterId"
                :configured-values="dashboardConfiguredFilters[filterId]!"
                :overridden="isOverridden(filterId)"
              />
            </div>
          </template>
          <CmkParagraph v-else class="db-runtime-filter-collection__empty-message">
            {{ displayLabels.emptyContextTitle }}
          </CmkParagraph>
        </div>
      </CollapsibleContent>
    </div>

    <div class="db-runtime-filter-collection__filter-container">
      <CollapsibleTitle
        :title="_t('Runtime filters')"
        :open="isOpen"
        @toggle-open="isOpen = !isOpen"
      />
      <CollapsibleContent :open="isOpen">
        <div class="db-runtime-filter-collection__items">
          <div
            v-for="(filterId, index) in filters"
            :key="index"
            class="db-runtime-filter-collection__item-container"
          >
            <slot
              :filter-id="filterId"
              :configured-filter-values="getFilterValues(filterId)"
              :index="index"
            />
          </div>
          <div v-if="additionalItemLabel" class="db-runtime-filter-collection__item-placeholder">
            <div class="db-runtime-filter-collection__item-placeholder-inner">
              {{ additionalItemLabel }}
            </div>
          </div>
        </div>
      </CollapsibleContent>
    </div>
  </div>
</template>

<style scoped>
.db-runtime-filter-collection__filter-container {
  margin-top: var(--dimension-5);
}

.db-runtime-filter-collection__items {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.db-runtime-filter-collection__item-container {
  background-color: var(--ux-theme-3);
  border: 1px solid var(--ux-theme-8);
}

.db-runtime-filter-collection__item-placeholder {
  padding: var(--dimension-7);
  border: 1px solid var(--ux-theme-8);
  color: var(--color-white-50);
}

.db-runtime-filter-collection__item-placeholder-inner {
  border: var(--color-midnight-grey-40) var(--dimension-1) dashed;
  background-color: var(--color-midnight-grey-80);
  padding: var(--dimension-3);
}

.db-runtime-filter-collection__empty-message {
  color: var(--menu-entry-disabled);
}
</style>
