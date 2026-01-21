<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkDropdown from '@/components/CmkDropdown'
import type { Suggestion } from '@/components/CmkSuggestions'

import CollapsibleContent from '@/dashboard/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard/components/filter/types'
import type { ContextFilters } from '@/dashboard/types/filter'
import type { ObjectType } from '@/dashboard/types/shared'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage1Header from '../../../components/Stage1Header.vue'
import FieldComponent from '../../../components/TableForm/FieldComponent.vue'
import FieldDescription from '../../../components/TableForm/FieldDescription.vue'
import TableForm from '../../../components/TableForm/TableForm.vue'
import TableFormRow from '../../../components/TableForm/TableFormRow.vue'
import SingleMultiWidgetObjectFilterConfiguration from '../../../components/filter/SingleMultiWidgetObjectFilterConfiguration.vue'
import type { ElementSelection } from '../../../types'

const { _t } = usei18n()

interface Stage1Props {
  contextFilters: ContextFilters
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  isInFilterSelectionMenuFocus: (objectType: ObjectType) => boolean
  inventoryPaths: Suggestion[]
  validationError?: string | undefined
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
const inventoryPath = defineModel<string | null>('inventoryPath', { required: true })
const hostObjectType = 'host'
const displayHwSwPropertySelection = ref(true)
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

  <CollapsibleTitle
    :title="_t('Metric selection')"
    :open="displayHwSwPropertySelection"
    class="collapsible"
    @toggle-open="displayHwSwPropertySelection = !displayHwSwPropertySelection"
  />
  <CollapsibleContent :open="displayHwSwPropertySelection">
    <TableForm>
      <TableFormRow>
        <FieldDescription>
          {{ _t('HW/SW inventory property') }}
        </FieldDescription>
        <FieldComponent>
          <div class="db-stage-contents__field-component-item">
            <CmkDropdown
              v-model:selected-option="inventoryPath"
              :input-hint="_t('Select inventory path')"
              :label="_t('Inventory path')"
              :options="{
                type: 'fixed',
                suggestions: props.inventoryPaths
              }"
            />
          </div>
          <CmkAlertBox v-if="props.validationError" variant="error">
            {{ props.validationError }}
          </CmkAlertBox>
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CollapsibleContent>
</template>

<style scoped>
.db-stage-contents__field-component-item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
