<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'

import type { FilterConfigState } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard/components/Wizard/types.ts'
import type { ConfiguredValues } from '@/dashboard/components/filter/types.ts'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

import WidgetObjectFilterConfiguration from './WidgetObjectFilterConfiguration/WidgetObjectFilterConfiguration.vue'
import { getStrings } from './utils'

const { _t } = usei18n()

interface Props {
  objectType: string
  configuredFiltersOfObjectType: FilterConfigState
  contextFilters: ContextFilters
  inSelectionMenuFocus: boolean
  singleOnly?: boolean
  availableFilterTypes?: ElementSelection[]
}

const props = withDefaults(defineProps<Props>(), {
  singleOnly: false,
  availableFilterTypes: () => [ElementSelection.SPECIFIC, ElementSelection.MULTIPLE]
})

const strings = computed(() => getStrings(props.objectType))

interface Emits {
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: string): void
  (e: 'remove-filter', filterId: string): void
}

const emit = defineEmits<Emits>()

const modeSelection = defineModel<ElementSelection>('modeSelection', {
  default: ElementSelection.SPECIFIC
})

const isSingleDisabled = computed(
  () => !props.availableFilterTypes?.includes(ElementSelection.SPECIFIC)
)
const isMultipleDisabled = computed(
  () => !props.availableFilterTypes?.includes(ElementSelection.MULTIPLE)
)
</script>

<template>
  <template v-if="!props.singleOnly">
    <CmkToggleButtonGroup
      :model-value="modeSelection"
      :options="[
        {
          label: _t('Single %{n}', { n: strings.singular }),
          value: ElementSelection.SPECIFIC,
          disabled: isSingleDisabled
        },
        {
          label: _t('Multiple %{n}', { n: strings.plural }),
          value: ElementSelection.MULTIPLE,
          disabled: isMultipleDisabled,
          disabledTooltip: isMultipleDisabled
            ? _t('Available in Checkmk Pro or higher.')
            : undefined
        }
      ]"
      @update:model-value="
        (value) => {
          modeSelection = value as ElementSelection
          emit('reset-object-type-filters', objectType)
        }
      "
    />
    <CmkIndent>
      <WidgetObjectFilterConfiguration
        :object-type="objectType"
        :object-selection-mode="modeSelection"
        :object-configured-filters="configuredFiltersOfObjectType"
        :in-focus="inSelectionMenuFocus"
        :context-filters="contextFilters"
        @set-focus="emit('set-focus', $event)"
        @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
        @remove-filter="(filterId) => emit('remove-filter', filterId)"
      />
    </CmkIndent>
  </template>
  <template v-else>
    <WidgetObjectFilterConfiguration
      :object-type="objectType"
      :object-selection-mode="ElementSelection.SPECIFIC"
      :object-configured-filters="configuredFiltersOfObjectType"
      :in-focus="inSelectionMenuFocus"
      :context-filters="contextFilters"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
  </template>
</template>
