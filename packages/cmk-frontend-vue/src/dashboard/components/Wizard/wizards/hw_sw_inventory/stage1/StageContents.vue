<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard/components/filter/types'
import type { ContextFilters } from '@/dashboard/types/filter'
import type { ObjectType } from '@/dashboard/types/shared'

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

const inventoryPathError = computed(() => {
  if (props.validationError) {
    return [props.validationError]
  }
  return undefined
})
</script>

<template>
  <Stage1Header @click="gotoNextStage" />

  <SectionBlock :title="_t('Host selection')">
    <CmkIndent>
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
    </CmkIndent>
  </SectionBlock>

  <SectionBlock :title="_t('Metric selection')">
    <CmkIndent>
      <div class="db-stage-contents__base-container">
        <CmkLabel style="font-weight: var(--font-weight-bold)">{{
          _t('HW/SW inventory property')
        }}</CmkLabel
        ><CmkLabelRequired space="before" />

        <ContentSpacer :dimension="4" />
        <div class="db-stage-contents__field-component-item">
          <CmkInlineValidation :validation="inventoryPathError" />
          <CmkDropdown
            v-model:selected-option="inventoryPath"
            width="fill"
            :input-hint="_t('Select inventory path')"
            :label="_t('Inventory path')"
            :options="{
              type: 'fixed',
              suggestions: props.inventoryPaths
            }"
            :form-validation="inventoryPathError !== undefined"
          />
        </div>
      </div>
    </CmkIndent>
  </SectionBlock>
</template>

<style scoped>
.db-stage-contents__base-container {
  background-color: var(--ux-theme-3);
  padding: 10px;
}

.db-stage-contents__field-component-item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
