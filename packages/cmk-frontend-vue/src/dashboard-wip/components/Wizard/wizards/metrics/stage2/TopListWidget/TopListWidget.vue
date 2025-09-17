<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import DataRangeInput from '@/dashboard-wip/components/Wizard/components/DataRangeInput/DataRangeInput.vue'
import FieldComponent from '@/dashboard-wip/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard-wip/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard-wip/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard-wip/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard-wip/components/Wizard/types.ts'

import type { UseTopList } from './composables/useTopList.ts'

const { _t } = usei18n()

defineProps<BaseWidgetProp>()

const handler = defineModel<UseTopList>('handler', { required: true })

defineExpose({ validate })

function validate(): boolean {
  return handler.value.validate()
}

const displayDataSettings = ref<boolean>(true)
const displayVisualizationSettings = ref<boolean>(true)
const widgetProps = computed(() => handler.value.widgetProps)
</script>

<template>
  <DashboardPreviewContent
    widget_id="gauge-preview"
    :dashboard-name="dashboardName"
    :general_settings="widgetProps.value!.general_settings!"
    :content="widgetProps.value!.content!"
    :effective_filter_context="widgetProps.value!.effective_filter_context!"
  />
  <ContentSpacer />

  <CmkCollapsibleTitle
    :title="_t('Data settings')"
    :open="displayDataSettings"
    class="collapsible"
    @toggle-open="displayDataSettings = !displayDataSettings"
  />
  <CmkCollapsible :open="displayDataSettings">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Date range') }}</FieldDescription>
        <FieldComponent>
          <DataRangeInput
            v-model:data-range-type="handler.dataRangeType.value"
            v-model:data-range-symbol="handler.dataRangeSymbol.value"
            v-model:data-range-min="handler.dataRangeMin.value"
            v-model:data-range-max="handler.dataRangeMax.value"
          />
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>{{ _t('Rankin order') }}</FieldDescription>
        <FieldComponent>
          <CmkDropdown
            :selected-option="handler.rankingOrder.value"
            :label="_t('Select option')"
            :options="{
              type: 'fixed',
              suggestions: [
                { name: 'high', title: _t('Top (highest) N') },
                { name: 'low', title: _t('Bottom (lowest) N') }
              ]
            }"
            @update:selected-option="
              (value) => (handler.rankingOrder.value = value === 'high' ? 'high' : 'low')
            "
          />
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>{{ _t('Limit to') }}</FieldDescription>
        <FieldComponent>
          <CmkInput
            v-model="handler.limitTo.value as number"
            type="number"
            :unit="_t('entries (max. %{max_entries})', { max_entries: `${handler.MAX_ENTRIES}` })"
            :external-errors="handler.limitToValidationErrors.value"
          />
        </FieldComponent>
      </TableFormRow>
      <TableFormRow>
        <FieldDescription>{{ _t('Columns') }}</FieldDescription>
        <FieldComponent>
          <div class="db-top-list-widget__item">
            <CmkCheckbox v-model="handler.showServiceName.value" :label="_t('Show service name')" />
          </div>
          <div class="db-top-list-widget__item">
            <CmkCheckbox
              v-model="handler.showBarVisualizaton.value"
              :label="_t('Show bar visualization')"
            />
          </div>
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCollapsible>

  <ContentSpacer />

  <CmkCollapsibleTitle
    :title="_t('Widget visualization')"
    :open="displayVisualizationSettings"
    class="collapsible"
    @toggle-open="displayVisualizationSettings = !displayVisualizationSettings"
  />
  <CmkCollapsible :open="displayVisualizationSettings">
    <WidgetVisualization
      v-model:show-title="handler.showTitle.value"
      v-model:show-title-background="handler.showTitleBackground.value"
      v-model:show-widget-background="handler.showWidgetBackground.value"
      v-model:title="handler.title.value"
      v-model:title-url="handler.titleUrl.value"
      v-model:title-url-enabled="handler.titleUrlEnabled.value"
      v-model:title-url-validation-errors="handler.titleUrlValidationErrors.value"
    />
  </CmkCollapsible>

  <ContentSpacer />
</template>

<style scoped>
.db-top-list-widget__item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
