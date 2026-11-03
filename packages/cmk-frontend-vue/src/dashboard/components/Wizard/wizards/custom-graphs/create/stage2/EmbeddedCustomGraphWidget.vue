<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { ref, watch } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import TimeRangeSource from '@/dashboard/components/TimeRange/TimeRangeSource.vue'
import GraphRenderOptions from '@/dashboard/components/Wizard/components/GraphRenderOptions/GraphRenderOptions.vue'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import WidgetVisualization from '@/dashboard/components/Wizard/components/WidgetVisualization/WidgetVisualization.vue'
import type { BaseWidgetProp, WidgetProps } from '@/dashboard/components/Wizard/types'
import GraphOptionRows from '@/graphing/designer/components/GraphOptionRows.vue'

import type { UseEmbeddedCustomGraph } from '../composables/useEmbeddedCustomGraph'

const { _t } = usei18n()

const { dashboardKey, tick, range, filters } = defineProps<
  BaseWidgetProp & { filters: ConfiguredFilters }
>()

const handler = defineModel<UseEmbeddedCustomGraph>('handler', { required: true })

const widgetProps = ref<WidgetProps | null>(null)
const updateWidgetProps = async () => {
  widgetProps.value = await handler.value.computeWidgetProps(filters)
}
void updateWidgetProps()
watch(
  [
    handler.value.dataSources,
    handler.value.followDashboardTimeRange,
    handler.value.timeRange,
    handler.value.visualization.widgetGeneralSettings,
    handler.value.renderOptions.graphRenderOptions,
    handler.value.graphOptions
  ],
  useDebounceFn(() => void updateWidgetProps(), 300),
  { deep: true }
)
</script>

<template>
  <DashboardPreviewContent
    v-if="widgetProps !== null"
    widget_id="graph-preview"
    :dashboard-key="dashboardKey"
    :tick="tick"
    :range="range"
    :general_settings="widgetProps.general_settings"
    :content="widgetProps.content"
    :effective-title="widgetProps.effectiveTitle"
    :effective_filter_context="widgetProps.effective_filter_context"
  />

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Data settings')" variant="padded">
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Time range') }}</FieldDescription>
        <FieldComponent>
          <TimeRangeSource
            v-model:follow-dashboard="handler.followDashboardTimeRange.value"
            v-model:selected-timerange="handler.timeRange.value"
          />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </CmkCatalogPanel>

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Widget settings')" variant="padded">
    <WidgetVisualization
      v-model:show-title="handler.visualization.showTitle.value"
      v-model:show-title-background="handler.visualization.showTitleBackground.value"
      v-model:show-widget-background="handler.visualization.showWidgetBackground.value"
      v-model:title="handler.visualization.title.value"
      v-model:title-url="handler.visualization.titleUrl.value"
      v-model:title-url-enabled="handler.visualization.titleUrlEnabled.value"
      v-model:title-url-validation-errors="handler.visualization.titleUrlValidationErrors.value"
      :title-macros="handler.visualization.titleMacros.value"
    />
  </CmkCatalogPanel>

  <ContentSpacer />

  <CmkCatalogPanel :title="_t('Additional graph options')" variant="padded" :open="false">
    <GraphRenderOptions
      v-model:horizontal-axis="handler.renderOptions.horizontalAxis.value"
      v-model:vertical-axis="handler.renderOptions.verticalAxis.value"
      v-model:vertical-axis-width-mode="handler.renderOptions.verticalAxisWidthMode.value"
      v-model:fixed-vertical-axis-width="handler.renderOptions.fixedVerticalAxisWidth.value"
      v-model:timestamp="handler.renderOptions.timestamp.value"
      v-model:round-margin="handler.renderOptions.roundMargin.value"
      v-model:graph-legend="handler.renderOptions.graphLegend.value"
      v-model:graph-legend-style="handler.renderOptions.graphLegendStyle.value"
      v-model:click-to-place-pin="handler.renderOptions.clickToPlacePin.value"
      v-model:show-burger-menu="handler.renderOptions.showBurgerMenu.value"
    >
      <template #after-axis>
        <GraphOptionRows
          v-model:graph-options="handler.graphOptionsForm"
          :validation-errors="handler.graphOptionErrors.value"
        />
      </template>
    </GraphRenderOptions>
  </CmkCatalogPanel>

  <ContentSpacer />
</template>
