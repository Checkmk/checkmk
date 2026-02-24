<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onBeforeMount } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import CatalogPanelHeader from '@/dashboard/components/Wizard/components/CatalogPanelHeader.vue'
import { ElementSelection } from '@/dashboard/components/Wizard/types.ts'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import { useVisualInfoCollection } from '@/dashboard/composables/api/useVisualInfoCollection'
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
  inFocus: boolean
  inViewContext?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  inViewContext: false
})

const { filterName } = getStrings(props.objectType)

const filterDefinitions = useFilterDefinitions()
const { ensureLoaded, byId: visualInfosById } = useVisualInfoCollection()

onBeforeMount(ensureLoaded)

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

const contextFilterTooltip = computed(() => {
  if (props.inViewContext) {
    return _t(
      `<b>Inherited view, default or runtime filters.</b><br />
      They apply unless:
      <ul>
        <li>Runtime filters are enabled to override default filters.</li>
        <li>Widget filters override view/default/runtime filters for this widget.</li>
      </ul>`
    )
  }
  return _t(
    `<b>Inherited default or runtime filters.</b><br />
    They apply unless:
    <ul>
      <li>Runtime filters are enabled to override default filters.</li>
      <li>Widget filters override default/runtime filters for this widget.</li>
    </ul>`
  )
})

const widgetFilterTooltip = computed(() => {
  if (props.inViewContext) {
    return _t(
      `Filters override view/default/runtime values for this widget only.<br />
       Required runtime filters must still be set on the dashboard level.`
    )
  }
  return _t(
    `Filters override default/runtime values for this widget only.<br />
     Required runtime filters must still be set on the dashboard level.`
  )
})

const contextFilterTitle = computed(() => {
  const isSpecific = props.objectSelectionMode === ElementSelection.SPECIFIC
  if (props.inViewContext) {
    return isSpecific ? _t('Applied filter') : _t('Applied filters')
  }
  if (isSpecific) {
    return _t('Applied dashboard %{n} filter', {
      n: filterName
    })
  }
  return _t('Applied dashboard %{n} filters', { n: props.objectType })
})

const emptyContextTitle = computed(() => {
  const isSpecific = props.objectSelectionMode === ElementSelection.SPECIFIC
  if (props.inViewContext) {
    const filterTitle = visualInfosById.value[props.objectType]?.title ?? props.objectType
    if (isSpecific) {
      return _t('No %{n} filter applied', { n: filterTitle })
    }
    return _t('No %{n} filters applied', { n: filterTitle })
  }
  if (isSpecific) {
    return _t('No dashboard %{n} filter applied', {
      n: filterName
    })
  }
  return _t('No dashboard %{n} filters applied', { n: props.objectType })
})
</script>

<template>
  <div class="db-widget-object-filter-configuration__group">
    <CmkCatalogPanel :title="contextFilterTitle" :open="false" variant="padded">
      <template #header>
        <CatalogPanelHeader :title="contextFilterTitle" :help-text="contextFilterTooltip" />
      </template>
      <!-- object-configured-filters is not being recognized as a props -->
      <!-- @vue-ignore -->
      <DisplayContextFilters
        :object-configured-filters="objectConfiguredFilters"
        :context-filters="relevantContextFilters"
        :empty-filters-title="emptyContextTitle"
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
      tooltip: widgetFilterTooltip
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
