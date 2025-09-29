<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n.ts'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'

import { ElementSelection } from '@/dashboard-wip/components/Wizard/types.ts'
import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import ObjectTypeFilterConfiguration from '../ObjectTypeFilterConfiguration/ObjectTypeFilterConfiguration.vue'
import type { FilterEmits } from '../types.ts'
import type { FilterConfigState } from '../utils.ts'
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

const filterDefinitions = useFilterDefinitions()
const toggleContextFiltersSection = ref(false)

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
  if (props.objectSelectionMode === ElementSelection.SPECIFIC) {
    return {
      contextFilterTitle: _t('Applied %{n} targeted filter', {
        n: props.objectType
      }),
      contextFilterTooltip: _t(
        'Relevant %{n} targeted filter set on dashboard level via dashboard or runtime filters.',
        {
          n: props.objectType
        }
      ),
      emptyContextTitle: _t('No %{n} targeted filter applied', {
        n: props.objectType
      }),
      emptyContextMessage: _t(
        'A %{n} targeted filter selected as dashboard or runtime filter appears here and applies to this widget. You can override the value by setting a widget specific filter.',
        {
          n: props.objectType
        }
      )
    }
  }
  return {
    contextFilterTitle: _t('Applied %{n} filters', { n: props.objectType }),
    contextFilterTooltip: _t(
      'Relevant %{n} filters set on dashboard level via dashboard or runtime filters.',
      { n: props.objectType }
    ),
    emptyContextTitle: _t('No %{n} filters applied', { n: props.objectType }),
    emptyContextMessage: _t(
      'Dashboard or runtime %{n} filters selected on dashboard level appear and apply to this widget. You can override the values by setting widget specific filters. ',
      { n: props.objectType }
    )
  }
})
</script>

<template>
  <div v-if="showContextFiltersSection">
    <CmkCollapsibleTitle
      :title="displayLabels.contextFilterTitle"
      :help_text="displayLabels.contextFilterTooltip"
      :open="toggleContextFiltersSection"
      @toggle-open="toggleContextFiltersSection = !toggleContextFiltersSection"
    />
    <CmkCollapsible :open="toggleContextFiltersSection">
      <!-- object-configured-filters is not being recognized as a props -->
      <!-- @vue-ignore -->
      <DisplayContextFilters
        :object-configured-filters="objectConfiguredFilters"
        :context-filters="relevantContextFilters"
        :empty-filters-title="displayLabels.emptyContextTitle"
        :empty-filters-message="displayLabels.emptyContextMessage"
      />
    </CmkCollapsible>
  </div>
  <ObjectTypeFilterConfiguration
    :object-type="objectType"
    :object-selection-mode="objectSelectionMode"
    :object-configured-filters="objectConfiguredFilters"
    :in-focus="inFocus"
    :filter-labels="{
      title: _t('Widget filters'),
      tooltip: _t('Widget configured filters override dashboard and runtime filters')
    }"
    @set-focus="emit('set-focus', $event)"
    @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
  />
</template>
