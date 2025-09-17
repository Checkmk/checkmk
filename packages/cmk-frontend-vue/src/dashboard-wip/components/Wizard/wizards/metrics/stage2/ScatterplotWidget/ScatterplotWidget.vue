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

import DashboardPreviewContent from '@/dashboard-wip/components/DashboardPreviewContent.vue'
import GraphTimeRange from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import FieldComponent from '@/dashboard-wip/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard-wip/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard-wip/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard-wip/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp } from '@/dashboard-wip/components/Wizard/types.ts'

import AdditionalOptions from './AdditionalOptions.vue'
import type { UseScatterplot } from './composables/useScatterplot.ts'

const { _t } = usei18n()

defineProps<BaseWidgetProp>()

const handler = defineModel<UseScatterplot>('handler', { required: true })

defineExpose({ validate })

function validate(): boolean {
  return handler.value.validate()
}

const displayDataSettings = ref<boolean>(true)
const displayVisualizationSettings = ref<boolean>(true)
const displayAdditionalSettings = ref<boolean>(false)
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
        <FieldDescription>{{ _t('Time range') }}</FieldDescription>
        <FieldComponent>
          <GraphTimeRange v-model:selected-timerange="handler.timeRange.value" />
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

  <CmkCollapsibleTitle
    :title="_t('Additional scatterplot options')"
    :open="displayAdditionalSettings"
    class="collapsible"
    @toggle-open="displayAdditionalSettings = !displayAdditionalSettings"
  />
  <CmkCollapsible :open="displayAdditionalSettings">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Scatterplot styling') }}</FieldDescription>
        <FieldComponent>
          <AdditionalOptions
            v-model:metric-color="handler.metricColor.value"
            v-model:average-color="handler.averageColor.value"
            v-model:median-color="handler.medianColor.value"
          />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCollapsible>

  <ContentSpacer />
</template>

<style scoped>
.db-scatterplot-widget__item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
