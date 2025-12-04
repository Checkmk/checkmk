<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard-wip/components/filter/types'
import type { ContextFilters } from '@/dashboard-wip/types/filter'
import type { ObjectType } from '@/dashboard-wip/types/shared'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage1Header from '../../../components/Stage1Header.vue'
import SingleMultiWidgetObjectFilterConfiguration from '../../../components/filter/SingleMultiWidgetObjectFilterConfiguration.vue'
import type { ElementSelection } from '../../../types'

const { _t } = usei18n()

interface Stage1Props {
  contextFilters: ContextFilters
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  isInFilterSelectionMenuFocus: (objectType: ObjectType) => boolean
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<{
  (e: 'go-next'): void
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: string): void
  (e: 'remove-filter', filterId: string): void
}>()

const gotoNextStage = () => {
  emit('go-next')
}

const hostFilterType = defineModel<ElementSelection>('hostFilterType', { required: true })
const hostObjectType = 'host'
</script>

<template>
  <Stage1Header @click="gotoNextStage" />

  <SectionBlock :title="_t('Host selection')">
    <SingleMultiWidgetObjectFilterConfiguration
      v-model:mode-selection="hostFilterType"
      :object-type="hostObjectType"
      :configured-filters-of-object-type="props.widgetConfiguredFilters"
      :context-filters="contextFilters"
      :in-selection-menu-focus="isInFilterSelectionMenuFocus(hostObjectType)"
      :single-only="true"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      @reset-object-type-filters="emit('reset-object-type-filters', $event)"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
  </SectionBlock>
</template>
