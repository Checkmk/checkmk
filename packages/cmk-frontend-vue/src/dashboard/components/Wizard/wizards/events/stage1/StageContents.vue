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
import WidgetObjectFilterConfiguration from '@/dashboard/components/Wizard/components/filter/WidgetObjectFilterConfiguration/WidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard/components/filter/types'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage1Header from '../../../components/Stage1Header.vue'

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
  (e: 'remove-filter', filterId: string): void
  (e: 'goNext'): void
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<Emits>()

const hostObjectType = 'host'
const eventObjectType = 'event'

// Filters
const filterDefinitions = useFilterDefinitions()
const configuredFiltersByObjectType = computed(() =>
  parseFilters(
    props.widgetConfiguredFilters,
    props.widgetActiveFilters,
    filterDefinitions,
    new Set(['host', 'event'])
  )
)
</script>

<template>
  <Stage1Header @click="emit('goNext')" />

  <SectionBlock :title="_t('Host selection')">
    <CmkIndent>
      <WidgetObjectFilterConfiguration
        :object-type="hostObjectType"
        :object-selection-mode="ElementSelection.MULTIPLE"
        :object-configured-filters="configuredFiltersByObjectType[hostObjectType] || {}"
        :in-focus="isInFilterSelectionMenuFocus(hostObjectType)"
        :context-filters="contextFilters"
        @set-focus="emit('set-focus', $event)"
        @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      />
    </CmkIndent>
  </SectionBlock>

  <SectionBlock :title="_t('Event selection')">
    <CmkIndent>
      <ObjectTypeFilterConfiguration
        :object-type="eventObjectType"
        :object-selection-mode="ElementSelection.MULTIPLE"
        :object-configured-filters="configuredFiltersByObjectType[eventObjectType] || {}"
        :in-focus="isInFilterSelectionMenuFocus(eventObjectType)"
        :filter-labels="{
          title: _t('Widget filters'),
          tooltip: _t('Widget configured filters override default and runtime filters')
        }"
        @set-focus="emit('set-focus', $event)"
        @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
        @remove-filter="(filterId) => emit('remove-filter', filterId)"
      />
    </CmkIndent>
  </SectionBlock>
</template>
