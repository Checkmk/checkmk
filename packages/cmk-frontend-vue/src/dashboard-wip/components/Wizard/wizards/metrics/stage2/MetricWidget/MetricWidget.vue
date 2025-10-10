<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import GraphTimeRange from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import DataRangeInput from '@/dashboard-wip/components/Wizard/components/DataRangeInput/DataRangeInput.vue'
import FieldComponent from '@/dashboard-wip/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard-wip/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard-wip/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard-wip/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import CollapsibleContent from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleContent.vue'
import CollapsibleTitle from '@/dashboard-wip/components/Wizard/components/collapsible/CollapsibleTitle.vue'
import type { BaseWidgetProp } from '@/dashboard-wip/components/Wizard/types.ts'

import type { UseMetric } from './composables/useMetric.ts'

const { _t } = usei18n()

defineProps<BaseWidgetProp>()

const handler = defineModel<UseMetric>('handler', { required: true })

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

  <CollapsibleTitle
    :title="_t('Data settings')"
    :open="displayDataSettings"
    class="collapsible"
    @toggle-open="displayDataSettings = !displayDataSettings"
  />
  <CollapsibleContent :open="displayDataSettings">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Time range') }}</FieldDescription>
        <FieldComponent>
          <CmkDropdown
            :selected-option="handler.timeRangeType.value"
            :label="_t('Select option')"
            :options="{
              type: 'fixed',
              suggestions: [
                { name: 'current', title: _t('Only show current value') },
                { name: 'window', title: _t('Show historic values') }
              ]
            }"
            @update:selected-option="
              (value) => {
                handler.timeRangeType.value = value === 'current' ? 'current' : 'window'
              }
            "
          />
          <CmkIndent v-if="handler.timeRangeType.value === 'window'">
            <GraphTimeRange v-model:selected-timerange="handler.timeRange.value" />
          </CmkIndent>
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>{{ _t('Data range') }}</FieldDescription>
        <FieldComponent>
          <DataRangeInput
            v-model:data-range-type="handler.dataRangeType.value"
            v-model:data-range-symbol="handler.dataRangeSymbol.value"
            v-model:data-range-max="handler.dataRangeMax.value"
            v-model:data-range-min="handler.dataRangeMin.value"
          />
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>{{ _t('Range limits') }}</FieldDescription>
        <FieldComponent>
          <CmkDropdown
            :selected-option="handler.displayRangeLimits.value ? '1' : '0'"
            :label="_t('Select option')"
            :options="{
              type: 'fixed',
              suggestions: [
                { name: '1', title: _t('Show the limits of values displayed') },
                { name: '0', title: _t('Don\'t show information of limits') }
              ]
            }"
            @update:selected-option="(value) => (handler.displayRangeLimits.value = value === '1')"
          />
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>{{ _t('Service status') }}</FieldDescription>
        <FieldComponent>
          <CmkCheckbox
            v-model="handler.showServiceStatus.value"
            :label="_t('Show service status')"
          />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CollapsibleContent>

  <ContentSpacer />

  <CollapsibleTitle
    :title="_t('Widget visualization')"
    :open="displayVisualizationSettings"
    class="collapsible"
    @toggle-open="displayVisualizationSettings = !displayVisualizationSettings"
  />
  <CollapsibleContent :open="displayVisualizationSettings">
    <WidgetVisualization
      v-model:show-title="handler.showTitle.value"
      v-model:show-title-background="handler.showTitleBackground.value"
      v-model:show-widget-background="handler.showWidgetBackground.value"
      v-model:title="handler.title.value"
      v-model:title-url="handler.titleUrl.value"
      v-model:title-url-enabled="handler.titleUrlEnabled.value"
      v-model:title-url-validation-errors="handler.titleUrlValidationErrors.value"
    />
  </CollapsibleContent>

  <ContentSpacer />
</template>

<style scoped>
.db-metric-widget__item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
