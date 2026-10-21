<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { ConfiguredFilters, ConfiguredValues } from 'cmk-ui-library/components/filter'
import { useFilterDefinitions } from 'cmk-ui-library/components/filter'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetObjectFilterConfiguration from '@/dashboard/components/Wizard/components/filter/WidgetObjectFilterConfiguration/WidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard/components/Wizard/types'
import { useInjectVisualInfos } from '@/dashboard/composables/useProvideVisualInfos'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'
import type { MonitoringTableName } from '@/monitoring/table-widget/tableDescriptors'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage1Header from '../../../components/Stage1Header.vue'
import { OFFERED_TABLES, monitoringTableViews } from '../monitoringTables'

const { _t } = usei18n()

interface Stage1Props {
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  contextFilters: ContextFilters
  currentFilterSelectionMenuFocus: ObjectType | null
  validationError?: string | undefined
}

const props = defineProps<Stage1Props>()

const emit = defineEmits<{
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'remove-filter', filterId: string): void
  (e: 'goNext'): void
}>()

const table = defineModel<MonitoringTableName | null>('table', { required: true })

const views = monitoringTableViews()
const visualInfosById = useInjectVisualInfos()
const filterDefinitions = useFilterDefinitions()

const infos = computed(() => (table.value === null ? [] : views[table.value].infos))

const configuredFiltersByObjectType = computed(() =>
  parseFilters(
    props.widgetConfiguredFilters,
    props.widgetActiveFilters,
    filterDefinitions,
    new Set(infos.value)
  )
)
</script>

<template>
  <Stage1Header :button-title="_t('Next step: Data configuration')" @click="emit('goNext')" />

  <SectionBlock :title="_t('View selection')">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('View') }}</FieldDescription>
        <FieldComponent>
          <CmkInlineValidation :validation="validationError ? [validationError] : []" />
          <CmkDropdown
            :model-value="table"
            :label="_t('View')"
            :input-hint="_t('Select view')"
            :options="{
              type: 'fixed',
              suggestions: OFFERED_TABLES.map((name) => ({ name, title: views[name].title }))
            }"
            :form-validation="!!validationError"
            @update:model-value="(value) => (table = value as MonitoringTableName | null)"
          />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </SectionBlock>

  <SectionBlock
    v-for="objectType in infos"
    :key="objectType"
    :title="untranslated(visualInfosById[objectType]?.title ?? objectType)"
  >
    <WidgetObjectFilterConfiguration
      :object-type="objectType"
      :object-selection-mode="ElementSelection.MULTIPLE"
      :object-configured-filters="configuredFiltersByObjectType[objectType] || {}"
      :in-focus="currentFilterSelectionMenuFocus === objectType"
      :context-filters="contextFilters"
      :in-view-context="true"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
  </SectionBlock>
</template>
