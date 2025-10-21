<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'

import type { FilterConfigState } from '@/dashboard-wip/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard-wip/components/Wizard/types.ts'
import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import WidgetObjectFilterConfiguration from './WidgetObjectFilterConfiguration/WidgetObjectFilterConfiguration.vue'

const { _t } = usei18n()

interface Props {
  objectType: string
  configuredFiltersOfObjectType: FilterConfigState
  contextFilters: ContextFilters
  inSelectionMenuFocus: boolean
  singleOnly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  singleOnly: false
})

interface Emits {
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: string): void
}

const emit = defineEmits<Emits>()

const modeSelection = defineModel<ElementSelection>('modeSelection', {
  default: ElementSelection.SPECIFIC
})
</script>

<template>
  <template v-if="!props.singleOnly">
    <ToggleButtonGroup
      v-model="modeSelection"
      :options="[
        { label: _t('Single %{n}', { n: props.objectType }), value: ElementSelection.SPECIFIC },
        {
          label: _t('Multiple %{n}', { n: props.objectType }),
          value: ElementSelection.MULTIPLE
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
    />
  </template>
</template>
