<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'

import ObjectTypeFilterConfiguration from '@/dashboard/components/Wizard/components/filter/ObjectTypeFilterConfiguration/ObjectTypeFilterConfiguration.vue'
import SingleMultiWidgetObjectFilterConfiguration from '@/dashboard/components/Wizard/components/filter/SingleMultiWidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard/components/filter/types'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage1Header from '../../../components/Stage1Header.vue'
import AvailableWidgets from '../../../components/WidgetSelection/AvailableWidgets.vue'
import { getAvailableGraphs, getAvailableWidgets } from '../composables/useSelectGraphTypes'

const { _t } = usei18n()

interface Stage1Props {
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  contextFilters: ContextFilters
  isInFilterSelectionMenuFocus: (objectType: ObjectType) => boolean
}

interface Emits {
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: ObjectType): void
  (e: 'remove-filter', filterId: string): void
  (e: 'goNext', preselectedWidgetType: string | null): void
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<Emits>()

const gotoNextStage = (preselectedWidgetType: string | null = null) => {
  emit('goNext', preselectedWidgetType)
}

const hostObjectType = 'host'
const serviceObjectType = 'service'
const logObjectType = 'log'

const hostFilterType = defineModel<ElementSelection>('hostFilterType', { required: true })
const serviceFilterType = defineModel<ElementSelection>('serviceFilterType', { required: true })

const availableWidgets = getAvailableWidgets()
const enabledWidgets = getAvailableGraphs()

// Filters
const filterDefinitions = useFilterDefinitions()
const configuredFiltersByObjectType = computed(() =>
  parseFilters(
    props.widgetConfiguredFilters,
    props.widgetActiveFilters,
    filterDefinitions,
    new Set(['host', 'service', 'log'])
  )
)
</script>

<template>
  <Stage1Header @click="gotoNextStage" />

  <SectionBlock :title="_t('Host selection')">
    <SingleMultiWidgetObjectFilterConfiguration
      v-model:mode-selection="hostFilterType"
      :object-type="hostObjectType"
      :configured-filters-of-object-type="configuredFiltersByObjectType[hostObjectType] || {}"
      :context-filters="contextFilters"
      :in-selection-menu-focus="isInFilterSelectionMenuFocus(hostObjectType)"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      @reset-object-type-filters="emit('reset-object-type-filters', $event)"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
  </SectionBlock>

  <SectionBlock :title="_t('Service selection')">
    <SingleMultiWidgetObjectFilterConfiguration
      v-model:mode-selection="serviceFilterType"
      :object-type="serviceObjectType"
      :configured-filters-of-object-type="configuredFiltersByObjectType[serviceObjectType] || {}"
      :context-filters="contextFilters"
      :in-selection-menu-focus="isInFilterSelectionMenuFocus(serviceObjectType)"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      @reset-object-type-filters="emit('reset-object-type-filters', $event)"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
  </SectionBlock>

  <SectionBlock :title="_t('Log selection')">
    <CmkIndent>
      <ObjectTypeFilterConfiguration
        :object-type="logObjectType"
        :object-selection-mode="ElementSelection.MULTIPLE"
        :object-configured-filters="configuredFiltersByObjectType[logObjectType] || {}"
        :in-focus="isInFilterSelectionMenuFocus(logObjectType)"
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
    </CmkIndent>
  </SectionBlock>

  <SectionBlock :title="_t('Available visualization types')">
    <AvailableWidgets
      :available-items="availableWidgets"
      :enabled-widgets="enabledWidgets"
      @select-widget="(preselectedWidgetType) => gotoNextStage(preselectedWidgetType)"
    />
  </SectionBlock>
</template>
