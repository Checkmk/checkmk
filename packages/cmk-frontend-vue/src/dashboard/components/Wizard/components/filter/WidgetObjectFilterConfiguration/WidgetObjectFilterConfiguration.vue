<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import CatalogPanelHeader from '@/dashboard/components/Wizard/components/CatalogPanelHeader.vue'
import { ElementSelection } from '@/dashboard/components/Wizard/types.ts'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

import ObjectTypeFilterConfiguration from '../ObjectTypeFilterConfiguration/ObjectTypeFilterConfiguration.vue'
import type { FilterEmits } from '../types.ts'
import type { FilterConfigState } from '../utils.ts'
import { getStrings } from '../utils.ts'
import DisplayContextFilters from './DisplayContextFilters.vue'

const { _t } = usei18n()

interface Props {
  objectType: ObjectType
  objectSelectionMode: ElementSelection
  objectConfiguredFilters: FilterConfigState
  contextFilters: ContextFilters
  showContextFiltersSection?: boolean
  inFocus: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showContextFiltersSection: true
})

const { filterName } = getStrings(props.objectType)

const filterDefinitions = useFilterDefinitions()

const emit = defineEmits<FilterEmits>()

const relevantContextFilters = computed<ContextFilters>(() => {
  if (props.objectSelectionMode === ElementSelection.SPECIFIC) {
    const singleTargetFilter = props.contextFilters[props.objectType as keyof ContextFilters]

    if (singleTargetFilter) {
      return {
        [props.objectType as keyof ContextFilters]: singleTargetFilter
      } as ContextFilters
    }
    return {}
  }

  const objectSpecificContext: ContextFilters = {}

  for (const [key, value] of Object.entries(props.contextFilters) as [
    keyof ContextFilters,
    ContextFilters[keyof ContextFilters]
  ][]) {
    const def = filterDefinitions[key as unknown as string]
    if (def === undefined) {
      throw new Error(`No filter definition found for filter ${String(key)}`)
    }

    if (def.extensions.info === props.objectType) {
      objectSpecificContext[key] = value
    }
  }

  return objectSpecificContext
})

const displayLabels = computed(() => {
  const tooltip = _t(
    `<b>Inherited default or runtime filters.</b><br />
    They apply unless:
    <ul>
      <li>Runtime filters are enabled to override default filters.</li>
      <li>Widget filters override default/runtime filters for this widget.</li>
    </ul>`
  )
  if (props.objectSelectionMode === ElementSelection.SPECIFIC) {
    return {
      contextFilterTitle: _t('Applied %{n} filter', {
        n: filterName
      }),
      contextFilterTooltip: tooltip,
      emptyContextTitle: _t('No %{n} filter applied', {
        n: filterName
      })
    }
  }
  return {
    contextFilterTitle: _t('Applied %{n} filters', { n: props.objectType }),
    contextFilterTooltip: tooltip,
    emptyContextTitle: _t('No %{n} filters applied', { n: props.objectType })
  }
})
</script>

<template>
  <div v-if="showContextFiltersSection" class="db-widget-object-filter-configuration__group">
    <CmkCatalogPanel :title="displayLabels.contextFilterTitle" :open="false" variant="padded">
      <template #header>
        <CatalogPanelHeader
          :title="displayLabels.contextFilterTitle"
          :help-text="displayLabels.contextFilterTooltip"
        />
      </template>
      <!-- object-configured-filters is not being recognized as a props -->
      <!-- @vue-ignore -->
      <DisplayContextFilters
        :object-configured-filters="objectConfiguredFilters"
        :context-filters="relevantContextFilters"
        :empty-filters-title="displayLabels.emptyContextTitle"
      />
    </CmkCatalogPanel>
  </div>
  <ObjectTypeFilterConfiguration
    :object-type="objectType"
    :object-selection-mode="objectSelectionMode"
    :object-configured-filters="objectConfiguredFilters"
    :in-focus="inFocus"
    :filter-labels="{
      title: _t('Widget filters'),
      tooltip: _t(
        `Filters override default/runtime values for this widget only.<br />
         Required runtime filters must still be set on the dashboard level.`
      )
    }"
    @set-focus="emit('set-focus', $event)"
    @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
    @remove-filter="(filterId) => emit('remove-filter', filterId)"
  />
</template>

<style scoped>
.db-widget-object-filter-configuration__group {
  padding-bottom: var(--dimension-4);
}
</style>
